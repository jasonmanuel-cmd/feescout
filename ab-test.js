/**
 * FeeScout Pricing A/B Test Engine
 * 
 * Client-side A/B testing with localStorage persistence.
 * Tracks: page views, CTA clicks, signup starts, signup completions.
 * Compatible with any analytics (GA4, Plausible, PostHog) via custom events.
 * 
 * Usage: Include this script on any pricing page. It auto-assigns a variant
 * and exposes window.feeScoutAB for manual tracking calls.
 */

(function() {
    'use strict';

    var TEST_NAME = 'pricing_2026_06';
    var VARIANT_KEY = 'feescout_ab_' + TEST_NAME;
    var STATS_KEY = 'feescout_ab_stats_' + TEST_NAME;

    // --- Variant Assignment ---
    function getVariant() {
        var stored = localStorage.getItem(VARIANT_KEY);
        if (stored === 'A' || stored === 'B') return stored;
        // 50/50 split
        var variant = Math.random() < 0.5 ? 'A' : 'B';
        localStorage.setItem(VARIANT_KEY, variant);
        return variant;
    }

    var currentVariant = getVariant();

    // --- Stats Tracking ---
    function getStats() {
        try {
            var raw = localStorage.getItem(STATS_KEY);
            return raw ? JSON.parse(raw) : { views: 0, ctaClicks: 0, signupStarts: 0, signupCompletes: 0 };
        } catch(e) { return { views: 0, ctaClicks: 0, signupStarts: 0, signupCompletes: 0 }; }
    }

    function saveStats(stats) {
        localStorage.setItem(STATS_KEY, JSON.stringify(stats));
    }

    function track(event) {
        var stats = getStats();
        if (event === 'view') stats.views++;
        if (event === 'cta_click') stats.ctaClicks++;
        if (event === 'signup_start') stats.signupStarts++;
        if (event === 'signup_complete') stats.signupCompletes++;
        saveStats(stats);

        // Dispatch custom event for analytics integration
        var detail = {
            test: TEST_NAME,
            variant: currentVariant,
            event: event,
            stats: stats,
            timestamp: Date.now()
        };
        window.dispatchEvent(new CustomEvent('feescout_ab', { detail: detail }));

        // Push to dataLayer for Google Analytics 4
        if (window.dataLayer) {
            window.dataLayer.push({
                event: 'feescout_ab_test',
                ab_test: TEST_NAME,
                ab_variant: currentVariant,
                ab_event: event
            });
        }

        // Plausible integration
        if (window.plausible) {
            window.plausible('AB Test: ' + TEST_NAME, {
                props: { variant: currentVariant, event: event }
            });
        }

        console.log('[FeeScout AB] ' + TEST_NAME + ' | Variant ' + currentVariant + ' | ' + event, stats);
    }

    // --- Public API ---
    window.feeScoutAB = {
        variant: currentVariant,
        test: TEST_NAME,
        track: track,
        getStats: getStats,
        reset: function() {
            localStorage.removeItem(VARIANT_KEY);
            localStorage.removeItem(STATS_KEY);
        }
    };

    // --- Auto-track page view ---
    track('view');

    // --- Auto-track CTA clicks ---
    document.addEventListener('click', function(e) {
        var target = e.target.closest('a, button');
        if (!target) return;
        var href = (target.href || '').toLowerCase();
        var text = (target.textContent || '').toLowerCase();
        var cls = (target.className || '').toLowerCase();

        // Track pricing CTA clicks
        if (cls.indexOf('cta-button') !== -1 || cls.indexOf('square-subscribe') !== -1 ||
            href.indexOf('square.link') !== -1 || href.indexOf('signup') !== -1 ||
            text.indexOf('subscribe') !== -1 || text.indexOf('get started') !== -1 ||
            text.indexOf('sign up') !== -1 || text.indexOf('upgrade') !== -1) {
            track('cta_click');
        }
    });

    // --- Auto-track signup modal opens ---
    var origOpenAuth = window.openAuthModal;
    if (origOpenAuth) {
        window.openAuthModal = function(mode) {
            if (mode === 'signup') track('signup_start');
            return origOpenAuth.apply(this, arguments);
        };
    }

    // --- Auto-track signup completion (intercept fetch) ---
    var origFetch = window.fetch;
    if (origFetch) {
        window.fetch = function(url, opts) {
            var urlStr = typeof url === 'string' ? url : url.url;
            if (urlStr && (urlStr.indexOf('/api/auth/signup') !== -1 || urlStr.indexOf('/api/auth/login') !== -1)) {
                return origFetch.apply(this, arguments).then(function(resp) {
                    if (resp.ok) track('signup_complete');
                    return resp;
                });
            }
            return origFetch.apply(this, arguments);
        };
    }

    console.log('[FeeScout AB] Test "' + TEST_NAME + '" active. Variant: ' + currentVariant);
    console.log('[FeeScout AB] View stats: window.feeScoutAB.getStats()');
    console.log('[FeeScout AB] Reset test: window.feeScoutAB.reset()');

})();
