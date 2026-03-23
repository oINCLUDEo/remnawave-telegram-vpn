package com.example.dev_vpn

import android.content.Intent
import android.content.SharedPreferences
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import androidx.annotation.RequiresApi

/**
 * Quick Settings tile for toggling the VPN connection.
 *
 * State is read from SharedPreferences written by the Flutter layer
 * (keys: vpn_tile_connected, vpn_tile_server_name).  The tile launches
 * the main activity to perform the actual connect/disconnect so that we
 * never duplicate VPN logic on the native side.
 */
@RequiresApi(Build.VERSION_CODES.N)
class VpnTileService : TileService() {

    companion object {
        const val PREFS_NAME = "FlutterSharedPreferences"
        const val KEY_CONNECTED = "flutter.vpn_tile_connected"
        const val KEY_SERVER = "flutter.vpn_tile_server_name"
        const val EXTRA_TILE_ACTION = "tile_toggle_vpn"
    }

    private val prefs: SharedPreferences
        get() = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)

    // ── TileService lifecycle ────────────────────────────────────────────────

    override fun onStartListening() {
        super.onStartListening()
        updateTile()
    }

    override fun onClick() {
        super.onClick()
        // Launch the main app with a flag so it can handle the VPN toggle.
        val intent = packageManager
            .getLaunchIntentForPackage(packageName)
            ?.apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(EXTRA_TILE_ACTION, true)
            }
        if (intent != null) {
            if (isLocked) {
                unlockAndRun { startActivity(intent) }
            } else {
                startActivity(intent)
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun updateTile() {
        val tile = qsTile ?: return
        val connected = prefs.getBoolean(KEY_CONNECTED, false)
        val serverName = prefs.getString(KEY_SERVER, null)

        tile.icon = Icon.createWithResource(this, R.mipmap.ic_launcher)
        tile.label = getString(R.string.vpn_tile_label)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.subtitle = if (connected && !serverName.isNullOrBlank()) serverName else null
        }

        tile.state = if (connected) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.updateTile()
    }
}
