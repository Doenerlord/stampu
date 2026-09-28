package com.stampu.app;

import android.os.Build;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import androidx.core.content.ContextCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    public class MonetBridge {
        @JavascriptInterface
        public String getMonetPrimary() {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try {
                    int color = ContextCompat.getColor(MainActivity.this, android.R.color.system_accent1_500);
                    return String.format("#%06X", (0xFFFFFF & color));
                } catch (Exception e) {
                    return null;
                }
            }
            return null;
        }

        @JavascriptInterface
        public String getMonetContainer() {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try {
                    int color = ContextCompat.getColor(MainActivity.this, android.R.color.system_accent1_100);
                    return String.format("#%06X", (0xFFFFFF & color));
                } catch (Exception e) {
                    return null;
                }
            }
            return null;
        }
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            WebView webView = getBridge().getWebView();
            if (webView != null) {
                webView.addJavascriptInterface(new MonetBridge(), "AndroidMonetBridge");
            }
        } catch (Exception e) {
            // bridge might initialize asynchronously
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        injectMonetTheme();
    }

    private void injectMonetTheme() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            try {
                int accent500 = ContextCompat.getColor(this, android.R.color.system_accent1_500);
                String hex = String.format("#%06X", (0xFFFFFF & accent500));
                WebView webView = getBridge().getWebView();
                if (webView != null) {
                    String js = "window.__ANDROID_MONET_PRIMARY__ = '" + hex + "'; " +
                                "if (typeof window.applyMonetColor === 'function') { window.applyMonetColor('" + hex + "'); }" +
                                "window.dispatchEvent(new CustomEvent('monet-color-detected', { detail: '" + hex + "' }));";
                    webView.post(() -> webView.evaluateJavascript(js, null));
                }
            } catch (Exception e) {
                // Ignore fallback
            }
        }
    }
}
