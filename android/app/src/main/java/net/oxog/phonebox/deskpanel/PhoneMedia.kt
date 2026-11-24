package net.oxog.phonebox.deskpanel

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.provider.Settings
import android.service.notification.NotificationListenerService
import android.util.Base64
import org.json.JSONObject
import java.io.ByteArrayOutputStream

/**
 * Studio GBRO fork: needed only so Android lets the app see the phone's media sessions (Deezer, Spotify…). It reads
 * no notification: the user grants "notification access" once and the class stays empty.
 */
class MediaAccessService : NotificationListenerService()

/**
 * Studio GBRO fork: what plays on the phone itself, for the "Phone music" widget: title, artist, app, a small cover,
 * and play / pause / next / previous. Nothing of it goes to the PC.
 */
object PhoneMedia {
    private var artKey: String? = null
    private var artData: String? = null

    fun hasAccess(context: Context): Boolean {
        val enabled = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners") ?: return false
        return enabled.split(':').any { ComponentName.unflattenFromString(it)?.packageName == context.packageName }
    }

    fun openAccessSettings(context: Context) {
        val i = Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try { context.startActivity(i) } catch (_: Exception) {
            context.startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }

    private fun controller(context: Context): MediaController? {
        if (!hasAccess(context)) return null
        val msm = context.getSystemService(Context.MEDIA_SESSION_SERVICE) as? MediaSessionManager ?: return null
        val list = try {
            msm.getActiveSessions(ComponentName(context, MediaAccessService::class.java))
        } catch (_: SecurityException) { return null }
        return list.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING } ?: list.firstOrNull()
    }

    fun state(context: Context): String {
        val j = JSONObject().put("access", hasAccess(context))
        val c = controller(context) ?: return j.toString()
        val md = c.metadata
        val title = md?.getString(MediaMetadata.METADATA_KEY_TITLE).orEmpty()
        val artist = md?.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: md?.getString(MediaMetadata.METADATA_KEY_ALBUM_ARTIST).orEmpty()
        val app = try {
            val pm = context.packageManager
            pm.getApplicationLabel(pm.getApplicationInfo(c.packageName, 0)).toString()
        } catch (_: Exception) { c.packageName }
        j.put("title", title).put("artist", artist).put("app", app)
            .put("playing", c.playbackState?.state == PlaybackState.STATE_PLAYING)
        val key = "${c.packageName}|$title|$artist"
        if (key != artKey) {
            artKey = key
            artData = (md?.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART) ?: md?.getBitmap(MediaMetadata.METADATA_KEY_ART))?.let { cover(it) }
        }
        artData?.let { j.put("art", it) }
        return j.toString()
    }

    /** A small JPEG of the cover as a data: URL (the widget shows it at most a few hundred pixels wide). */
    private fun cover(b: Bitmap): String? = try {
        val side = 256
        val scaled = if (b.width > side || b.height > side) {
            val f = side.toFloat() / maxOf(b.width, b.height)
            Bitmap.createScaledBitmap(b, maxOf(1, (b.width * f).toInt()), maxOf(1, (b.height * f).toInt()), true)
        } else b
        val out = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.JPEG, 80, out)
        "data:image/jpeg;base64," + Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    } catch (_: Exception) { null }

    fun command(context: Context, cmd: String): Boolean {
        val t = controller(context)?.transportControls ?: return false
        when (cmd) {
            "play" -> t.play()
            "pause" -> t.pause()
            "next" -> t.skipToNext()
            "previous" -> t.skipToPrevious()
            else -> return false
        }
        return true
    }
}
