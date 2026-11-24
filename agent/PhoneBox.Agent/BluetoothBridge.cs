using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Text;
using System.Text.Json;

namespace PhoneBox.Agent;

/// <summary>
/// Studio GBRO fork: the phone over Bluetooth, for computers whose firewall or network keeps Wi-Fi out.
///
/// The phone is paired once in Windows' Bluetooth settings. Its app offers a Bluetooth service (RFCOMM, secure: paired
/// devices only, encrypted by Bluetooth); this agent looks through the paired phones and connects to the one offering
/// it. The connection is outgoing, so the agent opens no port and Windows asks for no firewall rule.
///
/// What the phone sends over the link is only ever forwarded to this agent's own Wi-Fi API on 127.0.0.1 (never to
/// another address or port), and that API still checks the pinned certificate and the paired key, exactly as over
/// Wi-Fi. Frames, both ways: type (1 byte), stream id (4 bytes), length (4 bytes, at most <see cref="MaxPayload"/>),
/// payload. The agent sends HELLO first (its name and certificate fingerprint) so the phone shows this PC's panel.
/// </summary>
public sealed class BluetoothBridge(ConfigStore cfg, ILogger<BluetoothBridge> log, string? fingerprint, int apiPort) : BackgroundService
{
    public static readonly Guid ServiceId = new("6f3c2a10-9b1e-4d6a-a7c2-5b0e8d4f1a37");
    private const byte Hello = 1, Open = 2, Data = 3, Close = 4, Ping = 5;
    private const int MaxPayload = 16 * 1024;
    private const int MaxStreams = 64;
    private static readonly TimeSpan Silence = TimeSpan.FromSeconds(20);

    /// <summary>"off", "searching" or "connected", for the log and the settings page.</summary>
    public string State { get; private set; } = "off";
    public string? Phone { get; private set; }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        if (!OperatingSystem.IsWindows() || fingerprint is null) return;
        await Task.Delay(TimeSpan.FromSeconds(3), ct);
        var lastLogged = "";
        while (!ct.IsCancellationRequested)
        {
            var c = cfg.Get();
            if (!c.Bluetooth.Enabled || !c.Lan.Enabled)
            {
                State = "off";
                await Task.Delay(TimeSpan.FromSeconds(10), ct);
                continue;
            }
            State = "searching";
            List<(ulong Address, string Name)> phones;
            try { phones = PairedPhones(); }
            catch (Exception e) { phones = []; if (lastLogged != e.Message) log.LogInformation("Bluetooth: cannot list paired devices ({Error})", lastLogged = e.Message); }
            foreach (var (address, name) in phones)
            {
                if (ct.IsCancellationRequested) break;
                var socket = await TryConnectAsync(address, ct);
                if (socket is null) continue;
                State = "connected";
                Phone = name;
                lastLogged = "";
                log.LogInformation("Bluetooth: connected to {Phone}", name);
                try { await RunAsync(socket, ct); }
                catch (OperationCanceledException) when (ct.IsCancellationRequested) { }
                catch (Exception e) { log.LogInformation("Bluetooth: link to {Phone} closed ({Error})", name, e.Message); }
                finally
                {
                    socket.Dispose();
                    State = "searching";
                    Phone = null;
                }
                break; // look again from the start: the same phone usually comes back first
            }
            await Task.Delay(TimeSpan.FromSeconds(5), ct);
        }
    }

    /// <summary>Connects to the app's service on one paired phone; null when it does not answer (app not running, out of range).</summary>
    [SupportedOSPlatform("windows")]
    private static async Task<Socket?> TryConnectAsync(ulong address, CancellationToken ct)
    {
        var socket = new Socket((AddressFamily)AfBth, SocketType.Stream, (ProtocolType)BthProtoRfcomm);
        // Winsock looks the service up by its id (SDP); a blocking connect, given a deadline by closing the socket
        var connect = Task.Run(() => socket.Connect(new BluetoothEndPoint(address, ServiceId)), CancellationToken.None);
        try
        {
            var done = await Task.WhenAny(connect, Task.Delay(TimeSpan.FromSeconds(12), ct));
            if (done == connect && connect.IsCompletedSuccessfully) return socket;
        }
        catch (OperationCanceledException) { }
        socket.Dispose();
        try { await connect; } catch { } // observe the failure of the abandoned attempt
        return null;
    }

    private async Task RunAsync(Socket socket, CancellationToken outer)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(outer);
        var ct = cts.Token;
        await using var link = new NetworkStream(socket, ownsSocket: false);
        var write = new SemaphoreSlim(1, 1);
        var streams = new ConcurrentDictionary<int, TcpClient>();
        var lastReceived = DateTime.UtcNow;

        async Task Send(byte type, int id, ReadOnlyMemory<byte> payload)
        {
            var header = new byte[9];
            header[0] = type;
            BinaryPrimitives.WriteInt32BigEndian(header.AsSpan(1), id);
            BinaryPrimitives.WriteInt32BigEndian(header.AsSpan(5), payload.Length);
            await write.WaitAsync(ct);
            try
            {
                await link.WriteAsync(header, ct);
                if (payload.Length > 0) await link.WriteAsync(payload, ct);
                await link.FlushAsync(ct);
            }
            finally { write.Release(); }
        }

        void Drop(int id)
        {
            if (streams.TryRemove(id, out var tcp)) tcp.Dispose();
        }

        // PC → phone: what the agent answers on a stream goes back as DATA frames
        async Task Pump(int id, TcpClient tcp)
        {
            var buf = new byte[MaxPayload];
            try
            {
                var s = tcp.GetStream();
                int n;
                while ((n = await s.ReadAsync(buf, ct)) > 0) await Send(Data, id, buf.AsMemory(0, n));
            }
            catch { }
            if (streams.TryRemove(id, out _))
            {
                tcp.Dispose();
                try { await Send(Close, id, ReadOnlyMemory<byte>.Empty); } catch { }
            }
        }

        var hello = JsonSerializer.SerializeToUtf8Bytes(new { v = 1, pc = Environment.MachineName, fp = fingerprint });
        await Send(Hello, 0, hello);

        // keepalive both ways: a phone out of range or an app that was closed leaves the link silent
        var keepalive = Task.Run(async () =>
        {
            try
            {
                while (!ct.IsCancellationRequested)
                {
                    await Task.Delay(TimeSpan.FromSeconds(5), ct);
                    if (DateTime.UtcNow - lastReceived > Silence) { cts.Cancel(); socket.Dispose(); break; }
                    await Send(Ping, 0, ReadOnlyMemory<byte>.Empty);
                }
            }
            catch { cts.Cancel(); }
        }, CancellationToken.None);

        try
        {
            var header = new byte[9];
            var payload = new byte[MaxPayload];
            while (!ct.IsCancellationRequested)
            {
                await link.ReadExactlyAsync(header, ct);
                var type = header[0];
                var id = BinaryPrimitives.ReadInt32BigEndian(header.AsSpan(1));
                var len = BinaryPrimitives.ReadInt32BigEndian(header.AsSpan(5));
                if (len is < 0 or > MaxPayload) throw new InvalidDataException("frame too large");
                await link.ReadExactlyAsync(payload.AsMemory(0, len), ct);
                lastReceived = DateTime.UtcNow;
                switch (type)
                {
                    case Open:
                        if (streams.Count >= MaxStreams || streams.ContainsKey(id)) { await Send(Close, id, ReadOnlyMemory<byte>.Empty); break; }
                        var tcp = new TcpClient { NoDelay = true };
                        try { await tcp.ConnectAsync(IPAddress.Loopback, apiPort, ct); } // only ever the agent's own API
                        catch { tcp.Dispose(); await Send(Close, id, ReadOnlyMemory<byte>.Empty); break; }
                        streams[id] = tcp;
                        _ = Pump(id, tcp);
                        break;
                    case Data:
                        if (streams.TryGetValue(id, out var target))
                        {
                            try { await target.GetStream().WriteAsync(payload.AsMemory(0, len), ct); }
                            catch { Drop(id); await Send(Close, id, ReadOnlyMemory<byte>.Empty); }
                        }
                        break;
                    case Close:
                        Drop(id);
                        break;
                    default:
                        break; // PING, or a frame type from a newer app
                }
            }
        }
        finally
        {
            cts.Cancel();
            foreach (var id in streams.Keys) Drop(id);
            try { await keepalive; } catch { }
        }
    }

    // ---- Windows Bluetooth (Winsock AF_BTH and the Bluetooth API in bthprops.cpl) ----

    private const int AfBth = 32, BthProtoRfcomm = 3;

    /// <summary>SOCKADDR_BTH (packed): family (2), Bluetooth address (8), service class id (16), port (4) = 30 bytes.</summary>
    private sealed class BluetoothEndPoint(ulong address, Guid service) : EndPoint
    {
        public override AddressFamily AddressFamily => (AddressFamily)AfBth;

        public override SocketAddress Serialize()
        {
            var sa = new SocketAddress((AddressFamily)AfBth, 30);
            var a = BitConverter.GetBytes(address);
            for (var i = 0; i < 8; i++) sa[2 + i] = a[i];
            var g = service.ToByteArray(); // the in-memory GUID layout Winsock expects
            for (var i = 0; i < 16; i++) sa[10 + i] = g[i];
            // port 0 (bytes 26-29): Windows finds the RFCOMM channel from the service id
            return sa;
        }

        public override EndPoint Create(SocketAddress socketAddress) => this;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SearchParams
    {
        public int Size;
        public int ReturnAuthenticated, ReturnRemembered, ReturnUnknown, ReturnConnected, IssueInquiry;
        public byte TimeoutMultiplier;
        public IntPtr Radio;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct DeviceInfo
    {
        public int Size;
        public ulong Address;
        public uint ClassOfDevice;
        public int Connected, Remembered, Authenticated;
        public SystemTime LastSeen, LastUsed;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 248)] public string Name;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct SystemTime { public ushort Year, Month, DayOfWeek, Day, Hour, Minute, Second, Milliseconds; }

    [DllImport("bthprops.cpl", SetLastError = true)] private static extern IntPtr BluetoothFindFirstDevice(ref SearchParams p, ref DeviceInfo info);
    [DllImport("bthprops.cpl", SetLastError = true)] private static extern int BluetoothFindNextDevice(IntPtr find, ref DeviceInfo info);
    [DllImport("bthprops.cpl")] private static extern int BluetoothFindDeviceClose(IntPtr find);

    /// <summary>The phones paired with this PC (device class "phone"); no radio or no Bluetooth gives an empty list.</summary>
    [SupportedOSPlatform("windows")]
    private static List<(ulong, string)> PairedPhones()
    {
        var list = new List<(ulong, string)>();
        var p = new SearchParams { Size = Marshal.SizeOf<SearchParams>(), ReturnAuthenticated = 1, ReturnRemembered = 1 };
        var info = new DeviceInfo { Size = Marshal.SizeOf<DeviceInfo>(), Name = "" };
        var find = BluetoothFindFirstDevice(ref p, ref info);
        if (find == IntPtr.Zero) return list;
        try
        {
            do
            {
                var majorClass = (info.ClassOfDevice >> 8) & 0x1F;
                if (info.Authenticated != 0 && majorClass == 0x02) list.Add((info.Address, info.Name ?? ""));
                info = new DeviceInfo { Size = Marshal.SizeOf<DeviceInfo>(), Name = "" };
            } while (BluetoothFindNextDevice(find, ref info) != 0);
        }
        finally { BluetoothFindDeviceClose(find); }
        return list;
    }
}
