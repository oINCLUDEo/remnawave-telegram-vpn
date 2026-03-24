package com.example.dev_vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.os.Build
import android.os.Bundle
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.ByteArrayOutputStream

class MainActivity : FlutterActivity() {

    private val CHANNEL = "apps.channel"

    /** MethodChannel for Quick Settings tile ↔ Flutter communication. */
    private val TILE_CHANNEL = "com.example.dev_vpn/tile"
    private var tileChannel: MethodChannel? = null

    /**
     * Picks up [VpnTileService.ACTION_TILE_TOGGLE] while the app is alive.
     * Clears the pending-action flag so that the Flutter cold-start path
     * does not double-toggle, then calls fireTileToggle().
     */
    private val tileToggleReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == VpnTileService.ACTION_TILE_TOGGLE) {
                // Clear the flag so Flutter's checkPendingTileAction returns false
                getSharedPreferences(VpnTileService.PREFS_NAME, MODE_PRIVATE)
                    .edit().putBoolean(VpnTileService.KEY_PENDING_ACTION, false).apply()
                fireTileToggle()
            }
        }
    }

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // ── Tile channel ───────────────────────────────────────────────────
        tileChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, TILE_CHANNEL)
        tileChannel!!.setMethodCallHandler { call, result ->
            when (call.method) {
                // Flutter calls this during _init() to detect a pending tile toggle.
                // Returns true once (clears the flag) so Flutter can call _toggleConnection().
                "checkPendingTileAction" -> {
                    val prefs = getSharedPreferences(VpnTileService.PREFS_NAME, MODE_PRIVATE)
                    val pending = prefs.getBoolean(VpnTileService.KEY_PENDING_ACTION, false)
                    if (pending) {
                        prefs.edit().putBoolean(VpnTileService.KEY_PENDING_ACTION, false).apply()
                    }
                    result.success(pending)
                }
                // Flutter calls this after every VPN state change so the tile refreshes.
                "notifyTileState" -> {
                    sendBroadcast(
                        Intent("com.example.dev_vpn.VPN_STATE_CHANGED").setPackage(packageName)
                    )
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }

        // ── Apps channel ───────────────────────────────────────────────────
        val pm = packageManager
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "getInstalledApps" -> {
                        try {
                            val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
                            val list = apps
                                .filter { pm.getLaunchIntentForPackage(it.packageName) != null }
                                .map {
                                    mapOf(
                                        "packageName" to it.packageName,
                                        "appName" to pm.getApplicationLabel(it).toString()
                                    )
                                }
                            result.success(list)
                        } catch (e: Exception) {
                            result.error("ERROR", e.message, null)
                        }
                    }
                    "getAppIcon" -> {
                        val packageName = call.argument<String>("packageName")
                        if (packageName == null) { result.success(null); return@setMethodCallHandler }
                        try {
                            val drawable = pm.getApplicationIcon(packageName)
                            val bitmap = if (drawable is BitmapDrawable) {
                                drawable.bitmap
                            } else {
                                val bmp = Bitmap.createBitmap(
                                    drawable.intrinsicWidth,
                                    drawable.intrinsicHeight,
                                    Bitmap.Config.ARGB_8888
                                )
                                val canvas = Canvas(bmp)
                                drawable.setBounds(0, 0, canvas.width, canvas.height)
                                drawable.draw(canvas)
                                bmp
                            }
                            val stream = ByteArrayOutputStream()
                            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
                            result.success(stream.toByteArray())
                        } catch (e: Exception) {
                            result.success(null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        registerTileReceiver()
        // Note: tile-toggle on cold-start is handled by Flutter's _init() via
        // the checkPendingTileAction MethodChannel call — not here — to avoid
        // timing issues with the Flutter engine not being ready yet.
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // If the app was backgrounded (not killed) when the tile was tapped,
        // the broadcast receiver already handled it and cleared KEY_PENDING_ACTION.
        // If for some reason it didn't (e.g. receiver was not registered yet),
        // handle it here.
        if (intent.getBooleanExtra(VpnTileService.EXTRA_TILE_ACTION, false)) {
            val prefs = getSharedPreferences(VpnTileService.PREFS_NAME, MODE_PRIVATE)
            if (prefs.getBoolean(VpnTileService.KEY_PENDING_ACTION, false)) {
                prefs.edit().putBoolean(VpnTileService.KEY_PENDING_ACTION, false).apply()
                fireTileToggle()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try { unregisterReceiver(tileToggleReceiver) } catch (_: Exception) {}
        tileChannel = null
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun registerTileReceiver() {
        val filter = IntentFilter(VpnTileService.ACTION_TILE_TOGGLE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(tileToggleReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(tileToggleReceiver, filter)
        }
    }

    private fun fireTileToggle() {
        tileChannel?.invokeMethod("tileToggleVpn", null)
    }

    companion object {
        /** Called by [TileToggleReceiver] when the app process is alive. */
        private var instance: MainActivity? = null

        fun requestTileToggle() {
            instance?.fireTileToggle()
        }
    }

    init {
        instance = this
    }
}


