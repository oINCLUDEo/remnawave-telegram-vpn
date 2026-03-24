package com.example.dev_vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import androidx.annotation.RequiresApi

/**
 * Quick Settings tile for toggling the VPN connection.
 *
 * On click it sends ACTION_TILE_TOGGLE broadcast.  MainActivity receives the
 * broadcast (or the intent extra when cold-starting) and invokes the Flutter
 * MethodChannel "com.example.dev_vpn/tile" → "tileToggleVpn".
 *
 * VPN state is read from SharedPreferences written by Flutter
 * (keys: vpn_tile_connected, vpn_tile_server_name).
 */
@RequiresApi(Build.VERSION_CODES.N)
class VpnTileService : TileService() {

    companion object {
        const val PREFS_NAME = "FlutterSharedPreferences"
        const val KEY_CONNECTED = "flutter.vpn_tile_connected"
        const val KEY_SERVER = "flutter.vpn_tile_server_name"
        /** Broadcast action sent by the tile; received by MainActivity. */
        const val ACTION_TILE_TOGGLE = "com.example.dev_vpn.TILE_TOGGLE_VPN"
        /** Intent extra put on the launch intent (cold-start path). */
        const val EXTRA_TILE_ACTION = "tile_toggle_vpn"
    }

    private val prefs: SharedPreferences
        get() = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)

    /** Listens for state-change confirmations from the Flutter side. */
    private val stateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            updateTile()
        }
    }

    // ── TileService lifecycle ────────────────────────────────────────────────

    override fun onStartListening() {
        super.onStartListening()
        val filter = IntentFilter("com.example.dev_vpn.VPN_STATE_CHANGED")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(stateReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(stateReceiver, filter)
        }
        updateTile()
    }

    override fun onStopListening() {
        super.onStopListening()
        try { unregisterReceiver(stateReceiver) } catch (_: Exception) {}
    }

    override fun onClick() {
        super.onClick()
        val connected = prefs.getBoolean(KEY_CONNECTED, false)

        // Optimistically flip the tile so feedback is instant
        prefs.edit().putBoolean(KEY_CONNECTED, !connected).apply()
        updateTile()

        // Send broadcast so MainActivity (if alive) handles it without
        // bringing the app to the foreground.
        val broadcast = Intent(ACTION_TILE_TOGGLE).setPackage(packageName)
        sendBroadcast(broadcast)

        // Also launch / bring-to-front the app in case it is not running.
        val launchIntent = packageManager
            .getLaunchIntentForPackage(packageName)
            ?.apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(EXTRA_TILE_ACTION, true)
            }
        if (launchIntent != null) {
            if (isLocked) {
                unlockAndRun { startActivity(launchIntent) }
            } else {
                startActivity(launchIntent)
            }
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun updateTile() {
        val tile = qsTile ?: return
        val connected = prefs.getBoolean(KEY_CONNECTED, false)
        val serverName = prefs.getString(KEY_SERVER, null)

        tile.icon = Icon.createWithResource(this, R.drawable.ic_vpn_tile)
        tile.label = getString(R.string.vpn_tile_label)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.subtitle = when {
                connected && !serverName.isNullOrBlank() -> serverName
                connected -> getString(R.string.vpn_tile_connected)
                else -> getString(R.string.vpn_tile_disconnected)
            }
        }

        tile.state = if (connected) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.updateTile()
    }
}

