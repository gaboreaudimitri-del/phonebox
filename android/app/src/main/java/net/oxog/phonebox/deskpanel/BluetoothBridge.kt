package net.oxog.phonebox.deskpanel

import android.annotation.SuppressLint
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.DataInputStream
import java.io.OutputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

/**
 * Studio GBRO fork: the link to the PC over Bluetooth, for computers whose firewall or network keeps Wi-Fi out.
 *
 * The phone and the PC are paired once in the system Bluetooth settings. The phone then offers a Bluetooth service
 * (RFCOMM, secure: only paired devices, encrypted by Bluetooth), and the agent on the PC connects to it on its own:
 * the PC makes an outgoing connection, so it opens no port and needs no firewall rule.
 *
 * On the phone, 127.0.0.1:[LOCAL_PORT] is forwarded over that link to the agent's Wi-Fi API on the PC's 127.0.0.1.
 * That API still needs the pinned certificate and the paired key, so the bridge adds a route, not a way around the
 * pairing: another app on the phone that reaches the local port meets the same TLS and key checks as on Wi-Fi.
 *
 * Frames, both ways: type (1 byte), stream id (4 bytes), length (4 bytes, at most [MAX_PAYLOAD]), payload.
 * The PC sends HELLO first (JSON: its name and certificate fingerprint), so the phone switches to that PC's panel.
 */
object BluetoothBridge {
    val SERVICE_ID: UUID = UUID.fromString("6f3c2a10-9b1e-4d6a-a7c2-5b0e8d4f1a37")
    const val LOCAL_PORT = 8767
    const val LOCAL_HOST = "127.0.0.1"
    const val PERMISSION_REQUEST = 4711
    const val CONNECT_PERMISSION = "android.permission.BLUETOOTH_CONNECT" // Android 12+ runtime permission

    private const val HELLO = 1
    private const val OPEN = 2
    private const val DATA = 3
    private const val CLOSE = 4
    private const val PING = 5
    private const val MAX_PAYLOAD = 16 * 1024
    private const val MAX_STREAMS = 64
    private const val SILENCE_MS = 20_000L

    /** The fingerprint and name of the PC on the other end, null while no PC is connected. */
    @Volatile var pcFingerprint: String? = null
        private set
    @Volatile var pcName: String? = null
        private set
    /** Called (on a background thread) with the fingerprint of a PC that just connected. */
    @Volatile var onPcConnected: ((String) -> Unit)? = null

    @Volatile private var started = false
    @Volatile private var link: Link? = null
    private val streams = ConcurrentHashMap<Int, Socket>()
    private val nextId = AtomicInteger(1)

    fun hasPermission(context: Context): Boolean =
        Build.VERSION.SDK_INT < 31 ||
            context.checkPermission(CONNECT_PERMISSION, android.os.Process.myPid(), android.os.Process.myUid()) == PackageManager.PERMISSION_GRANTED

    /** Starts the bridge once (idempotent). Without the Bluetooth permission, nothing happens. */
    @Synchronized
    fun start(context: Context) {
        if (started || !hasPermission(context)) return
        val manager = context.applicationContext.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager ?: return
        val adapter = manager.adapter ?: return // no Bluetooth on this phone
        started = true
        Thread({ localServer() }, "bt-local").apply { isDaemon = true }.start()
        Thread({ bluetoothServer(adapter) }, "bt-rfcomm").apply { isDaemon = true }.start()
    }

    @SuppressLint("MissingPermission") // checked in start()
    private fun bluetoothServer(adapter: android.bluetooth.BluetoothAdapter) {
        while (true) {
            var server: BluetoothServerSocket? = null
            try {
                if (!adapter.isEnabled) { Thread.sleep(5000); continue }
                server = adapter.listenUsingRfcommWithServiceRecord("PhoneBox GBRO", SERVICE_ID)
                val socket = server.accept() // blocks until a paired PC connects
                try { server.close() } catch (_: Exception) {}
                server = null
                serve(socket)
            } catch (_: InterruptedException) {
                return
            } catch (_: Exception) {
                try { server?.close() } catch (_: Exception) {}
                try { Thread.sleep(3000) } catch (_: InterruptedException) { return }
            }
        }
    }

    private class Link(val socket: BluetoothSocket) {
        private val out: OutputStream = socket.outputStream
        @Volatile var lastReceived = System.currentTimeMillis()

        @Synchronized
        fun send(type: Int, id: Int, payload: ByteArray = ByteArray(0), length: Int = payload.size) {
            val h = ByteArray(9)
            h[0] = type.toByte()
            h[1] = (id ushr 24).toByte(); h[2] = (id ushr 16).toByte(); h[3] = (id ushr 8).toByte(); h[4] = id.toByte()
            h[5] = (length ushr 24).toByte(); h[6] = (length ushr 16).toByte(); h[7] = (length ushr 8).toByte(); h[8] = length.toByte()
            out.write(h)
            if (length > 0) out.write(payload, 0, length)
            out.flush()
        }

        fun close() { try { socket.close() } catch (_: Exception) {} }
    }

    /** One PC connection: reads frames until the link breaks, while a watchdog pings and drops a silent link. */
    private fun serve(socket: BluetoothSocket) {
        val l = Link(socket)
        link = l
        val watchdog = Thread({
            try {
                while (link === l) {
                    Thread.sleep(5000)
                    if (System.currentTimeMillis() - l.lastReceived > SILENCE_MS) { l.close(); break }
                    l.send(PING, 0)
                }
            } catch (_: Exception) { l.close() }
        }, "bt-watchdog").apply { isDaemon = true }
        watchdog.start()
        try {
            val input = DataInputStream(BufferedInputStream(socket.inputStream, 32 * 1024))
            while (true) {
                val type = input.readUnsignedByte()
                val id = input.readInt()
                val len = input.readInt()
                if (len < 0 || len > MAX_PAYLOAD) break // not our protocol: drop the link
                val payload = ByteArray(len)
                input.readFully(payload)
                l.lastReceived = System.currentTimeMillis()
                when (type) {
                    HELLO -> {
                        val j = JSONObject(String(payload, Charsets.UTF_8))
                        val fp = j.optString("fp").lowercase().takeIf { Regex("^[0-9a-f]{64}$").matches(it) }
                        pcName = j.optString("pc").filter { it >= ' ' }.take(64)
                        pcFingerprint = fp
                        if (fp != null) try { onPcConnected?.invoke(fp) } catch (_: Exception) {}
                    }
                    DATA -> streams[id]?.let { s ->
                        try { s.getOutputStream().write(payload); s.getOutputStream().flush() } catch (_: Exception) { closeStream(id, notify = true) }
                    }
                    CLOSE -> closeStream(id, notify = false)
                    PING -> {}
                    else -> {} // unknown frame types are ignored (a newer agent)
                }
            }
        } catch (_: Exception) {
            // link broken
        } finally {
            link = null
            pcFingerprint = null
            pcName = null
            l.close()
            for (id in java.util.Collections.list(streams.keys())) closeStream(id, notify = false) // keys(): API 1
        }
    }

    private fun closeStream(id: Int, notify: Boolean) {
        val s = streams.remove(id) ?: return
        try { s.close() } catch (_: Exception) {}
        if (notify) try { link?.send(CLOSE, id) } catch (_: Exception) {}
    }

    /** 127.0.0.1:[LOCAL_PORT] on the phone: each connection becomes a stream to the agent while a PC is connected. */
    private fun localServer() {
        while (true) {
            try {
                ServerSocket(LOCAL_PORT, 50, InetAddress.getByName(LOCAL_HOST)).use { server ->
                    while (true) {
                        val s = server.accept()
                        val l = link
                        if (l == null || streams.size >= MAX_STREAMS) { try { s.close() } catch (_: Exception) {}; continue }
                        val id = nextId.getAndIncrement() and 0x7fffffff
                        s.tcpNoDelay = true
                        streams[id] = s
                        try { l.send(OPEN, id) } catch (_: Exception) { closeStream(id, notify = false); continue }
                        Thread({ pump(id, s, l) }, "bt-stream-$id").apply { isDaemon = true }.start()
                    }
                }
            } catch (_: Exception) {
                try { Thread.sleep(3000) } catch (_: InterruptedException) { return }
            }
        }
    }

    /** Phone → PC: what the panel writes on a local connection goes out as DATA frames. */
    private fun pump(id: Int, s: Socket, l: Link) {
        val buf = ByteArray(MAX_PAYLOAD)
        try {
            val input = s.getInputStream()
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                if (n > 0) l.send(DATA, id, buf, n)
            }
        } catch (_: Exception) {
        } finally {
            if (streams.remove(id) != null) {
                try { s.close() } catch (_: Exception) {}
                try { l.send(CLOSE, id) } catch (_: Exception) {}
            }
        }
    }
}
