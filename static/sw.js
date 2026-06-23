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
            .then(windowClients => {
                // Check if there is already a window/tab open with the target URL
                for (let client of windowClients) {
                    if (client.url === origin + url && 'focus' in client) {
                        return client.focus();
                    }
                }
                // If not, open a new window/tab
                if (clients.openWindow) {
                    return clients.openWindow(origin + url);
                }
            })
    );
});