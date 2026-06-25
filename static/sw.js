// ============================================================
//  PWA OFFLINE / CACHING (added)
// ============================================================

const CACHE_NAME = 'guan-v1';
const OFFLINE_URL = '/offline';

// List of core assets to cache on install
const ASSETS = [
  '/',
  '/dashboard',
  '/profile',
  '/search',
  '/static/style.css',
  '/static/icon-192.png',
  '/static/icon-512.png',
  OFFLINE_URL
];

// Install event – cache core assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(ASSETS);
      })
      .then(function() {
        return self.skipWaiting();
      })
  );
});

// Activate event – clean old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(name) {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch event – try network first, fallback to cache
self.addEventListener('fetch', function(event) {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;
  // Skip non-http(s) requests
  if (!event.request.url.startsWith('http')) return;

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // If valid response, clone and cache it for future
        if (response && response.status === 200) {
          var cloned = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, cloned);
          });
        }
        return response;
      })
      .catch(function() {
        // Network failed – serve from cache or offline page
        return caches.match(event.request)
          .then(function(cached) {
            return cached || caches.match(OFFLINE_URL);
          });
      })
  );
});

// ============================================================
//  YOUR EXISTING PUSH NOTIFICATION HANDLERS (unchanged)
// ============================================================

self.addEventListener('push', function(event) {
    if (!(self.Notification && self.Notification.permission === 'granted')) {
        return;
    }

    let data = {};
    try {
        data = event.data.json();
    } catch (e) {
        data = {
            title: 'New notification',
            body: event.data ? event.data.text() : 'You have a new update',
            icon: '/static/ram-icon.png'
        };
    }

    const title = data.title || 'GuAn';
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/ram-icon.png',
        badge: data.badge || '/static/badge.png',
        data: data.data || {},
        requireInteraction: true,
        tag: data.tag || 'guan-notification'
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    const url = event.notification.data?.url || '/dashboard';
    const origin = self.location.origin;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(function(windowClients) {
                for (let client of windowClients) {
                    if (client.url === origin + url && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(origin + url);
                }
            })
    );
});