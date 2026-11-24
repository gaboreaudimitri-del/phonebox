using System.Text.Json;

namespace PhoneBox.Agent;

/// <summary>
/// Studio GBRO fork: the professional controls added once to every configuration (new or existing), so a colleague
/// has them without any setup. Afterwards they are ordinary shortcuts: they can be edited or removed in the settings,
/// and they do not come back (the version of what was added is remembered in "gbroSeed").
/// </summary>
public static class GbroDefaults
{
    private const int Version = 1;

    private static readonly Shortcut[] Shortcuts =
    [
        // Windows' own call mute (Win+Alt+K): works with Teams without bringing its window to the front
        new() { Id = "gbro-teams-mic", Label = "Micro Teams", Icon = "🎙️", Color = "#6264a7", Cmd = "builtin:keys", Args = "win+alt+k" },
        // the other Teams keys act on the Teams window: it is brought to the front first ("msteams:" opens Teams)
        new() { Id = "gbro-teams-front", Label = "Ouvrir Teams", Icon = "💬", Color = "#6264a7", Cmd = "msteams:" },
        Macro("gbro-teams-camera", "Caméra Teams", "📷", "ctrl+shift+o"),
        Macro("gbro-teams-hand", "Lever la main", "✋", "ctrl+shift+k"),
        Macro("gbro-teams-share", "Partager l'écran", "🖥️", "ctrl+shift+e"),
        Macro("gbro-teams-leave", "Quitter la réunion", "📴", "ctrl+shift+h", "#ef4444"),
        new() { Id = "gbro-outlook-mail", Label = "Nouveau mail", Icon = "✉️", Color = "#0078d4", Cmd = "outlook.exe", Args = "/c ipm.note" },
        new() { Id = "gbro-outlook-calendar", Label = "Calendrier", Icon = "📅", Color = "#0078d4", Cmd = "outlook.exe", Args = "/select outlook:calendar" },
        new() { Id = "gbro-lock", Label = "Verrouiller", Icon = "🔒", Color = "#ef4444", Cmd = "builtin:lock" },
    ];

    private static Shortcut Macro(string id, string label, string icon, string keys, string color = "#6264a7") => new()
    {
        Id = id, Label = label, Icon = icon, Color = color, Cmd = "builtin:macro",
        Steps = ["shortcut:gbro-teams-front", "wait:700", "keys:" + keys],
    };

    /// <summary>The Meeting controls widget lists the "meeting" controls: one per Teams key.</summary>
    private static readonly (string Id, string Label, string Shortcut)[] Meeting =
    [
        ("gbro-meeting-mic", "Micro", "gbro-teams-mic"),
        ("gbro-meeting-camera", "Caméra", "gbro-teams-camera"),
        ("gbro-meeting-hand", "Main levée", "gbro-teams-hand"),
        ("gbro-meeting-share", "Partager", "gbro-teams-share"),
        ("gbro-meeting-leave", "Quitter", "gbro-teams-leave"),
    ];

    public static void Apply(ConfigStore store, ILogger? log = null)
    {
        try
        {
            var c = JsonSerializer.Deserialize<AgentConfig>(JsonSerializer.Serialize(store.Get(), ConfigStore.WriteOpts), ConfigStore.ReadOpts);
            if (c is null || c.GbroSeed >= Version) return;
            foreach (var s in Shortcuts)
                if (!c.Shortcuts.Any(x => x.Id == s.Id)) c.Shortcuts.Add(s);
            foreach (var (id, label, shortcut) in Meeting)
                if (!c.Controls.Actions.Any(a => a.Id == id))
                    c.Controls.Actions.Add(new DeckAction { Id = id, Label = label, Kind = "meeting", Target = shortcut });
            c.GbroSeed = Version;
            var error = store.Save(JsonSerializer.Serialize(c, ConfigStore.WriteOpts), store.Version);
            if (error is null) log?.LogInformation("PhoneBox: Teams, Outlook and lock controls added");
            else log?.LogInformation("PhoneBox: controls not added ({Error})", error);
        }
        catch (Exception e) { log?.LogInformation("PhoneBox: controls not added ({Error})", e.Message); }
    }
}
