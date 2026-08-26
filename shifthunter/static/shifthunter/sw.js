self.addEventListener("push", (event) => {
    let data = {};

    try {
        data = event.data ? event.data.json() : {};
    } catch (error) {
        data = {
            title: "Shyftr Shift Alert",
            body: event.data ? event.data.text() : "New matching shift.",
        };
    }

    const title = data.title || "Shyftr Shift Alert";

    const options = {
        body: data.body || "A new shift matches your preferences.",
        icon: data.icon || "/static/shifthunter/icon-192.png",
        badge: data.badge || "/static/shifthunter/icon-192.png",
        data: {
            url: data.url || "/",
        },
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    const url = event.notification.data?.url || "/";

    event.waitUntil(
        clients.matchAll({
            type: "window",
            includeUncontrolled: true,
        }).then((clientList) => {
            for (const client of clientList) {
                if ("focus" in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }

            return clients.openWindow(url);
        })
    );
});
