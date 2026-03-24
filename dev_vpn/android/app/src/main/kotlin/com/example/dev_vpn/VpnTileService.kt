package com.example.dev_vpn

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
 * The tile reads **real** VPN state from [ConnectivityManager] (TRANSPORT_VPN),
 * not from SharedPreferences, so it is always accurate even when the Flutter
 * app process is not running.
 *
 * ## Toggle
 * On click the tile sets KEY_PENDING_ACTION in SharedPreferences and then:
 *  1. Sends ACTION_TILE_TOGGLE broadcast – MainActivity picks this up when the
 *     app is alive in the background.
 *  2. Launches the app – on a cold start Flutter reads KEY_PENDING_ACTION via
 *     the "checkPendingTileAction" MethodChannel call in _init() and calls
 *     _toggleConnection().
 *
 * There is NO optimistic flip.  The tile state is always derived from the
 * system network stack, so it cannot get out of sync.
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

        // If the app is alive the broadcast reaches MainActivity's receiver.
        sendBroadcast(Intent(ACTION_TILE_TOGGLE).setPackage(packageName))

        // Also launch / bring app to front so Flutter can handle the toggle
        // (required for both cold-start and backgrounded cases).
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

    /**
     * Returns true when there is an active VPN transport on the device,
     * regardless of whether the Flutter app is running.
     */
    private fun isVpnActive(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val caps = cm.getNetworkCapabilities(network) ?: return false
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)
        } else {
            @Suppress("DEPRECATION")
            cm.activeNetworkInfo?.type == ConnectivityManager.TYPE_VPN
        }
    }

    private fun updateTile() {
        val tile = qsTile ?: return
        val vpnActive = isVpnActive()
        val serverName = prefs.getString(KEY_SERVER, null)

        // Keep SharedPreferences in sync so Flutter sees the correct state on
        // next startup (e.g. if the VPN was stopped via the system notification).
        prefs.edit().putBoolean(KEY_CONNECTED, vpnActive).apply()

        tile.icon = Icon.createWithResource(this, R.drawable.ic_vpn_tile)
        tile.label = getString(R.string.vpn_tile_label)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.subtitle = when {
                vpnActive && !serverName.isNullOrBlank() -> serverName
                vpnActive -> null
                else -> getString(R.string.vpn_tile_disconnected)
            }
        }

        tile.state = if (vpnActive) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.updateTile()
    }
}


