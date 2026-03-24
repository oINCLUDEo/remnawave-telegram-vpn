package com.example.dev_vpn

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.graphics.drawable.Icon
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import androidx.annotation.RequiresApi

/**
 * Quick Settings tile for toggling the VPN connection.
 *
 * ## State
 * The tile reads VPN state from SharedPreferences written by Flutter
 * (key: vpn_tile_connected).  Flutter updates this key on every VPN state
 * change via _persistTileState → notifyTileState MethodChannel call.
 *
 * A sanity check in [onStartListening] resets the pref to false if the
 * system has no active VPN transport (catches the case where the app was
 * killed while connected and the pref was left as true).
 *
 * ## Toggle
 * On click the tile sets KEY_PENDING_ACTION in SharedPreferences and then:
 *  1. Sends ACTION_TILE_TOGGLE broadcast – MainActivity picks this up when the
 *     app is alive in the background.
 *  2. Calls startActivityAndCollapse() to bring the app to the foreground.
 *     Flutter reads KEY_PENDING_ACTION in _init() via checkPendingTileAction
 *     MethodChannel and calls _toggleConnection().
 */
@RequiresApi(Build.VERSION_CODES.N)
class VpnTileService : TileService() {

    companion object {
        const val PREFS_NAME = "FlutterSharedPreferences"
        const val KEY_CONNECTED = "flutter.vpn_tile_connected"
        const val KEY_SERVER = "flutter.vpn_tile_server_name"
        /** Set to true by the tile on click; cleared by Flutter after acting on it. */
        const val KEY_PENDING_ACTION = "flutter.vpn_tile_pending_action"
        /** Broadcast action sent by the tile; received by MainActivity. */
        const val ACTION_TILE_TOGGLE = "com.example.dev_vpn.TILE_TOGGLE_VPN"
        /** Intent extra put on the launch intent (cold-start path). */
        const val EXTRA_TILE_ACTION = "tile_toggle_vpn"
    }

    private val prefs: SharedPreferences
        get() = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)

    /** Listens for VPN_STATE_CHANGED broadcast sent by MainActivity after state changes. */
    private val stateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            updateTile()
        }
    }

    // ── TileService lifecycle ────────────────────────────────────────────────

    override fun onStartListening() {
        super.onStartListening()

        // Sanity check: if Flutter left the pref as "connected" but no VPN
        // transport is active (app was killed while VPN was on), reset the flag.
        if (prefs.getBoolean(KEY_CONNECTED, false) && !isVpnActive()) {
            prefs.edit().putBoolean(KEY_CONNECTED, false).apply()
        }

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

        // Mark that the user wants a toggle.  Flutter will clear this flag once
        // it has acted on it (via checkPendingTileAction MethodChannel call).
        prefs.edit().putBoolean(KEY_PENDING_ACTION, true).apply()

        // If the app activity is alive the broadcast alone is enough: the
        // tileToggleReceiver in MainActivity handles it without showing any UI.
        sendBroadcast(Intent(ACTION_TILE_TOGGLE).setPackage(packageName))

        if (MainActivity.isActive) {
            // App is running — broadcast already handled; no activity launch needed.
            return
        }

        // Cold start: launch the app.  MainActivity.onCreate will call
        // moveTaskToBack(true) immediately so the user never sees the UI.
        // Flutter initializes in the background and _checkPendingTileAction
        // fires the toggle once the engine is ready.
        val launchIntent = packageManager
            .getLaunchIntentForPackage(packageName)
            ?.apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra(EXTRA_TILE_ACTION, true)
            } ?: return

        val startAction = Runnable {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val pi = PendingIntent.getActivity(
                    this, 0, launchIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                startActivityAndCollapse(pi)
            } else {
                @Suppress("DEPRECATION")
                startActivityAndCollapse(launchIntent)
            }
        }

        if (isLocked) {
            unlockAndRun(startAction)
        } else {
            startAction.run()
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    /**
     * Returns true when any network on the device has a VPN transport active.
     * Uses allNetworks (not just activeNetwork) so split-tunnel configurations
     * are detected correctly.
     */
    private fun isVpnActive(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            cm.allNetworks.any { network ->
                cm.getNetworkCapabilities(network)
                    ?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true
            }
        } else {
            @Suppress("DEPRECATION")
            cm.activeNetworkInfo?.type == ConnectivityManager.TYPE_VPN
        }
    }

    /**
     * Reads tile state from SharedPreferences that Flutter keeps up-to-date.
     * This is more reliable than querying ConnectivityManager directly because
     * the VPN transport reported by the system may differ from what the
     * flutter_v2ray plugin actually established.
     */
    private fun updateTile() {
        val tile = qsTile ?: return
        val connected = prefs.getBoolean(KEY_CONNECTED, false)
        val serverName = prefs.getString(KEY_SERVER, null)

        tile.icon = Icon.createWithResource(this, R.drawable.ic_vpn_tile)
        tile.label = getString(R.string.vpn_tile_label)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.subtitle = when {
                connected && !serverName.isNullOrBlank() -> serverName
                connected -> null
                else -> getString(R.string.vpn_tile_disconnected)
            }
        }

        tile.state = if (connected) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.updateTile()
    }
}



