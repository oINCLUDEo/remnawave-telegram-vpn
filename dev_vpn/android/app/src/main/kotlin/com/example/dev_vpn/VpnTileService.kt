package com.example.dev_vpn

import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import androidx.annotation.RequiresApi
import android.content.SharedPreferences

/**
 * Android Quick Settings tile that lets the user toggle the VPN connection
 * without opening the app.
 *
 * State is kept in sync via SharedPreferences (key: "vpn_connected"), which
 * the Flutter side writes whenever the VPN connects or disconnects.
 */
@RequiresApi(Build.VERSION_CODES.N)
class VpnTileService : TileService() {

    companion object {
        private const val PREFS_NAME = "FlutterSharedPreferences"
        private const val KEY_CONNECTED = "flutter.vpn_connected"
        private const val KEY_SERVER_NAME = "flutter.vpn_server_name"
    }

    // ── Lifecycle ──────────────────────────────────────────────────────────────

    override fun onStartListening() {
        super.onStartListening()
        updateTile()
    }

    override fun onStopListening() {
        super.onStopListening()
    }

    override fun onClick() {
        super.onClick()
        val connected = isVpnConnected()
        if (connected) {
            // Disconnect: send broadcast that the Flutter app / VPN service handles
            sendDisconnectBroadcast()
        } else {
            // Connect: open the app so the user can connect
            launchApp()
        }
        // Optimistically update the tile state; the real state will follow
        // when the Flutter side writes to SharedPreferences and onStartListening
        // fires again.
        setTileState(active = !connected, label = if (connected) null else serverName())
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun prefs(): SharedPreferences =
        applicationContext.getSharedPreferences(PREFS_NAME, MODE_PRIVATE)

    private fun isVpnConnected(): Boolean = prefs().getBoolean(KEY_CONNECTED, false)

    private fun serverName(): String? = prefs().getString(KEY_SERVER_NAME, null)

    private fun updateTile() {
        val connected = isVpnConnected()
        setTileState(active = connected, label = if (connected) serverName() else null)
    }

    private fun setTileState(active: Boolean, label: String?) {
        val tile = qsTile ?: return
        tile.state = if (active) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.subtitle = label ?: if (active) "Подключено" else "Отключено"
        }
        tile.icon = Icon.createWithResource(
            applicationContext,
            R.mipmap.ic_launcher
        )
        tile.updateTile()
    }

    private fun sendDisconnectBroadcast() {
        val intent = Intent("com.example.dev_vpn.VPN_DISCONNECT")
        intent.setPackage(packageName)
        sendBroadcast(intent)
        // Also try stopping VPN service directly via v2ray_box action
        try {
            val stopIntent = Intent("com.example.v2ray_box.action.STOP_VPN_SERVICE")
            stopIntent.setPackage(packageName)
            sendBroadcast(stopIntent)
        } catch (_: Exception) { /* ignore if service not available */ }
    }

    private fun launchApp() {
        val intent = packageManager.getLaunchIntentForPackage(packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
        } ?: return
        startActivityAndCollapse(intent)
    }
}
