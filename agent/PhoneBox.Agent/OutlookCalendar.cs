using System.Runtime.Versioning;

namespace PhoneBox.Agent;

/// <summary>
/// Studio GBRO fork: the calendar of the classic Outlook installed on this computer, read through its own programming
/// interface (COM) — no published link, no cloud access, nothing leaves the PC. Used by a calendar whose address is
/// "outlook". Needs classic Outlook (the new Outlook and Outlook on the web have no such interface); Outlook is
/// started in the background if it is not running. Only the title, times and place of each event are read.
/// </summary>
public static class OutlookCalendar
{
    public const string Address = "outlook";

    public static bool IsOutlook(string url) => url.Trim().Equals(Address, StringComparison.OrdinalIgnoreCase)
        || url.Trim().StartsWith(Address + ":", StringComparison.OrdinalIgnoreCase);

    public static Task<List<CalendarEvent>> ReadAsync(DateTime fromUtc, DateTime toUtc, string name, string color)
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("Outlook is only read on Windows");
        var tcs = new TaskCompletionSource<List<CalendarEvent>>();
        // COM objects of Outlook want a single-threaded apartment
        var t = new Thread(() =>
        {
            try { tcs.SetResult(Read(fromUtc, toUtc, name, color)); }
            catch (Exception e) { tcs.SetException(e); }
        }) { IsBackground = true, Name = "outlook-calendar" };
        t.SetApartmentState(ApartmentState.STA);
        t.Start();
        return tcs.Task.WaitAsync(TimeSpan.FromSeconds(60));
    }

    [SupportedOSPlatform("windows")]
    private static List<CalendarEvent> Read(DateTime fromUtc, DateTime toUtc, string name, string color)
    {
        var type = Type.GetTypeFromProgID("Outlook.Application")
            ?? throw new InvalidOperationException("classic Outlook is not installed on this computer");
        dynamic app = Activator.CreateInstance(type)!;
        dynamic ns = app.GetNamespace("MAPI");
        dynamic folder = ns.GetDefaultFolder(9); // olFolderCalendar
        dynamic items = folder.Items;
        items.IncludeRecurrences = true;
        items.Sort("[Start]");
        var from = fromUtc.ToLocalTime();
        var to = toUtc.ToLocalTime();
        // Outlook's filter takes local times written the way this computer writes dates (short date + short time)
        var fmt = System.Globalization.CultureInfo.CurrentCulture.DateTimeFormat;
        string F(DateTime d) => d.ToString(fmt.ShortDatePattern + " " + fmt.ShortTimePattern, System.Globalization.CultureInfo.CurrentCulture);
        dynamic found = items.Restrict($"[Start] < '{F(to)}' AND [End] > '{F(from)}'");
        var list = new List<CalendarEvent>();
        var count = 0;
        // GetFirst / GetNext: with recurrences included, Count is meaningless and foreach is not reliable over COM
        for (dynamic? it = found.GetFirst(); it is not null; it = found.GetNext())
        {
            if (++count > 500) break; // a runaway recurring series
            try
            {
                if ((int)it.Class != 26) continue; // olAppointment
                DateTime start = it.Start, end = it.End;
                bool allDay = it.AllDayEvent;
                // olFree = 0: invitations kept as free (and declined ones Outlook keeps) are left out
                if ((int)it.BusyStatus == 0 && !allDay) continue;
                string title = it.Subject ?? "";
                string? location = it.Location;
                list.Add(new CalendarEvent(title.Trim(), Ms(start), Ms(end), allDay,
                    string.IsNullOrWhiteSpace(location) ? null : location.Trim(), name, color));
            }
            catch { /* one unreadable item does not hide the others */ }
        }
        return list;
    }

    private static long Ms(DateTime local) => new DateTimeOffset(DateTime.SpecifyKind(local, DateTimeKind.Local)).ToUnixTimeMilliseconds();
}
