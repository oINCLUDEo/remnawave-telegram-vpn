package com.example.dev_vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Receives [VpnTileService.ACTION_TILE_TOGGLE] broadcasts and forwards the
 * toggle request to Flutter via the MethodChannel registered in [MainActivity].
 *
 * If the app is not yet running the broadcast will be ignored and the
 * cold-start path in [MainActivity.onNewIntent] / [MainActivity.onCreate]
 * handles the toggle instead.
 */
class TileToggleReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != VpnTileService.ACTION_TILE_TOGGLE) return
        // Delegate to MainActivity so the MethodChannel is already set up.
        MainActivity.requestTileToggle()
    }
}
