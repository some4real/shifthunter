console.log('🔥 SHIFTHUNTER NEW DASHBOARD JS LOADED');

const fallback = [
    {
        id: 'SH-88421',
        location: 'DHS - 151 East',
        start: '2026-09-09T04:00:00Z',
        end: '2026-09-09T12:00:00Z',
        schedule: 'Grave',
        pay: 141.53,
        distance: 2.4,
        autoassignable: true,
        status: 'available',
        priority: 'primary'
    },
    {
        id: 'SH-88437',
        location: 'DHS - 4380 Bronx',
        start: '2026-09-09T04:00:00Z',
        end: '2026-09-09T12:00:00Z',
        schedule: 'Grave',
        pay: 141.53,
        distance: 8.7,
        autoassignable: true,
        status: 'available',
        priority: 'normal'
    },
    {
        id: 'SH-88452',
        location: 'DHS - 151 East',
        start: '2026-09-16T04:00:00Z',
        end: '2026-09-16T12:00:00Z',
        schedule: 'Grave',
        pay: 141.53,
        distance: 2.4,
        autoassignable: false,
        status: 'available',
        priority: 'primary'
    },
    {
        id: 'SH-88466',
        location: 'DHS - 281 Park',
        start: '2026-09-10T12:00:00Z',
        end: '2026-09-10T20:00:00Z',
        schedule: 'Day',
        pay: 134.20,
        distance: 5.1,
        autoassignable: true,
        status: 'available',
        priority: 'normal'
    }
];

let shifts = fallback;
let onlyAuto = false;
let preferences = null;

const $ = id => document.getElementById(id);

function date(v) {
    return new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    }).format(new Date(v));
}

function time(v) {
    return new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        hour: 'numeric',
        minute: '2-digit'
    }).format(new Date(v));
}

function render() {
    const q = $('query').value.toLowerCase();
    const site = $('site').value;
    const monitoring = preferences?.monitoring;

const prioritySite =
    monitoring?.priority_site?.trim().toLowerCase() || '';

const secondarySites =
    (monitoring?.secondary_sites || '')
        .split(',')
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

const allowedSites = [
    prioritySite,
    ...secondarySites
].filter(Boolean);

    const rows = shifts.filter(
        s =>
            s.location.toLowerCase().includes(q) &&
            (site === 'All sites' || s.location === site) &&
            s.status !== 'clocked_out' &&
            (!onlyAuto || s.autoassignable)
    );
    $('available').textContent = rows.length;

    $('primary').textContent =
        rows.filter(s => s.priority === 'primary').length;

    $('pay').textContent =
        '$' + rows.reduce((a, s) => a + (s.pay || 0), 0).toFixed(2);

    $('rows').innerHTML = rows.length
        ? rows.map(s => `
            <article>
                <div>
                    <b>
                        <i class="dot ${s.priority}"></i>
                        ${s.location}
                        ${s.priority === 'primary'
                            ? '<em>PRIMARY</em>'
                            : ''}
                    </b>
                    <small>${s.id}</small>
                </div>

                <div>
                    <strong>${s.schedule}</strong>
                    ${date(s.start)}
                </div>

                <div>
                    ◷ ${time(s.start)} – ${time(s.end)}
                </div>

                <div>
                    ⌖ ${s.distance == null ? '—' : s.distance + ' mi'}
                </div>

                <div>
                    <b>
                        ${s.pay == null
                            ? '—'
                            : '$' + s.pay.toFixed(2)}
                    </b>
                </div>

                <div>
                    <i class="online"></i>
                Available
                </div>
            </article>
        `).join('')
        : `
            <div class="empty">
                No shifts match your filters
                <small>
                    Try clearing your search or changing the site filter.
                </small>
            </div>
        `;

    renderMonitoringMatches();
}

async function refresh() {
    const button = $('refresh');

    button.disabled = true;
    button.querySelector('span').textContent = 'Checking…';

    $('error').hidden = true;

    try {
        const r = await fetch(
            '/api/shyftr/shifts',
            { cache: 'no-store' }
        );

        if (!r.ok) {
            throw Error();
        }

        const data = await r.json();

        shifts = data.shifts;

        $('connection').innerHTML =
            '<i class="live"></i> Connected to Shyftr';

        $('detail').textContent = 'live response';

    } catch (e) {

        shifts = fallback;

        $('connection').innerHTML =
            '<i></i> Preview mode';

        $('error').hidden = false;

        $('error').textContent =
            'Live API unavailable. Showing the latest preview data.';

        $('detail').textContent = 'fallback data';

    } finally {

        $('checked').textContent =
            new Date().toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit'
            });

        button.disabled = false;

        button.querySelector('span').textContent =
            'Refresh shifts';

        fillSites();
        render();
    }
}

function matchesMonitoring(shift) {
    const monitoring = preferences?.monitoring;

    if (!monitoring?.enabled) {
        return false;
    }

    const location = (shift.location || '').toLowerCase();

    const prioritySite =
        (monitoring.priority_site || '').trim().toLowerCase();

    const secondarySites =
        (monitoring.secondary_sites || '')
            .split(',')
            .map(s => s.trim().toLowerCase())
            .filter(Boolean);

    const matchedPriority =
        prioritySite &&
        location.includes(prioritySite);

    const matchedSecondary =
        secondarySites.some(site =>
            location.includes(site)
        );

    if (!matchedPriority && !matchedSecondary) {
        return false;
    }

    if (shift.status === 'clocked_out') {
        return false;
    }

    if (
        monitoring.require_autoassignable &&
        !shift.autoassignable
    ) {
        return false;
    }
    const start = new Date(shift.start);
const end = new Date(shift.end);

const localParts = new Intl.DateTimeFormat('en-US', {
    timeZone: monitoring.timezone || 'America/New_York',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
}).formatToParts(start);

const parts = Object.fromEntries(
    localParts.map(p => [p.type, p.value])
);

const weekdayMap = {
    Mon: 0,
    Tue: 1,
    Wed: 2,
    Thu: 3,
    Fri: 4,
    Sat: 5,
    Sun: 6
};

const shiftWeekday = weekdayMap[parts.weekday];

const shiftStartMinutes =
    Number(parts.hour) * 60 +
    Number(parts.minute);

const configuredWeekday =
    Number(monitoring.weekday);

const [startHour, startMinute] =
    (monitoring.start_time || '00:00')
        .split(':')
        .map(Number);

const [endHour, endMinute] =
    (monitoring.end_time || '23:59')
        .split(':')
        .map(Number);

const windowStart =
    startHour * 60 + startMinute;

const windowEnd =
    endHour * 60 + endMinute;

if (shiftWeekday !== configuredWeekday) {
    return false;
}

if (windowStart <= windowEnd) {
    if (
        shiftStartMinutes < windowStart ||
        shiftStartMinutes > windowEnd
    ) {
        return false;
    }
} else {
    // Overnight monitoring window.
    if (
        shiftStartMinutes < windowStart &&
        shiftStartMinutes > windowEnd
    ) {
        return false;
    }
}

    const minimumHours =
        Number(monitoring.minimum_hours || 0);

    const hours =
        (end - start) / (1000 * 60 * 60);

    if (hours < minimumHours) {
        return false;
    }

    const minimumValue =
        Number(monitoring.minimum_value || 0);

    if (Number(shift.pay || 0) < minimumValue) {
        return false;
    }

    return {
        priority: Boolean(matchedPriority),
        secondary: Boolean(matchedSecondary),
        hours,
    };
}
function renderMonitoringMatches() {
    const box = $('monitorMatches');
    const rows = $('monitorMatchRows');
    const count = $('monitorMatchCount');

    if (!preferences?.monitoring?.enabled) {
        box.hidden = true;
        return;
    }

    const matches = shifts
        .filter(s => s.status !== 'clocked_out')
        .map(shift => ({
            shift,
            match: matchesMonitoring(shift)
        }))
        .filter(item => item.match);

    count.textContent = matches.length;

    if (!matches.length) {
        box.hidden = true;
        return;
    }

    box.hidden = false;

    rows.innerHTML = matches.map(({ shift, match }) => `
        <div class="monitor-match">
            <b class="${match.priority ? 'primary-match' : ''}">
                ${match.priority ? '🚨 PRIMARY MATCH' : '● MONITORING MATCH'}
                — ${shift.location}
            </b>

            <small>
                ${shift.schedule}
                · ${date(shift.start)}
                · ${time(shift.start)} – ${time(shift.end)}
                · ${match.hours.toFixed(1)} hrs
                · $${Number(shift.pay || 0).toFixed(2)}
            </small>
        </div>
    `).join('');
}
function fillSites() {
    const current = $('site').value;

    const names = [
        'All sites',
        ...new Set(shifts.map(s => s.location))
    ];

    $('site').innerHTML =
        names.map(n => `<option>${n}</option>`).join('');

    $('site').value =
        names.includes(current)
            ? current
            : 'All sites';
}


/* =========================
   SETTINGS
========================= */

function openSettings() {
    $('settingsOverlay').hidden = false;
    loadPreferences();
}

function closeSettings() {
    $('settingsOverlay').hidden = true;
    $('settingsMessage').hidden = true;
}

async function loadPreferences() {
    try {
        const response = await fetch(
            '/api/preferences',
            { cache: 'no-store' }
        );

        if (!response.ok) {
            throw Error();
        }

        preferences = await response.json();

        const monitoring = preferences.monitoring;
        const auto = preferences.auto_pick;

        $('monitoringEnabled').checked =
            monitoring.enabled;

        $('prioritySite').value =
            monitoring.priority_site || '';

        $('secondarySites').value =
            monitoring.secondary_sites || '';

        $('weekday').value =
            monitoring.weekday;

        $('startTime').value =
            monitoring.start_time;

        $('endTime').value =
            monitoring.end_time;

        $('minimumHours').value =
            monitoring.minimum_hours;

        $('minimumValue').value =
            monitoring.minimum_value;

        $('requireAutoassignable').checked =
            monitoring.require_autoassignable;

        $('pushEnabled').checked =
            monitoring.push_enabled;

        $('emailEnabled').checked =
            monitoring.email_enabled;

        $('emailAddress').value =
            monitoring.email_address || '';

        $('autoPickEnabled').checked =
            auto.enabled;

        $('autoPickShiftType').value =
            auto.shift_type || '';

        $('autoPickMinimumHours').value =
            auto.minimum_hours;

        $('autoPickMinimumValue').value =
            auto.minimum_value;

        $('autoPickRequireAutoassignable').checked =
            auto.require_autoassignable;

        updateAutoPickStatus();

        $('monitoringStatus').textContent =
            monitoring.enabled
                ? 'MONITORING ACTIVE'
                : 'MONITORING PAUSED';

    } catch (error) {

        showSettingsMessage(
            'Unable to load settings.',
            true
        );
    }
}

function updateAutoPickStatus() {
    const enabled =
        $('autoPickEnabled').checked;

    const warning =
        $('autoPickWarning');

    const status =
        $('autoPickStatus');

    if (enabled) {
        warning.hidden = false;

        status.innerHTML =
            'Claim endpoint: <strong>Not configured</strong>';
    } else {
        warning.hidden = true;

        status.innerHTML =
            'Claim endpoint: <strong>Not configured</strong>';
    }
}

async function saveSettings() {
    const button = $('saveSettings');

    button.disabled = true;
    button.textContent = 'Saving…';

    $('settingsMessage').hidden = true;

    const payload = {
        monitoring: {
            enabled:
                $('monitoringEnabled').checked,

            priority_site:
                $('prioritySite').value,

            secondary_sites:
                $('secondarySites').value,

            weekday:
                Number($('weekday').value),

            start_time:
                $('startTime').value,

            end_time:
                $('endTime').value,

            minimum_hours:
                $('minimumHours').value,

            minimum_value:
                $('minimumValue').value,

            require_autoassignable:
                $('requireAutoassignable').checked,

            push_enabled:
                $('pushEnabled').checked,

            email_enabled:
                $('emailEnabled').checked,

            email_address:
                $('emailAddress').value
        },

        auto_pick: {
            enabled:
                $('autoPickEnabled').checked,

            shift_type:
                $('autoPickShiftType').value,

            minimum_hours:
                $('autoPickMinimumHours').value,

            minimum_value:
                $('autoPickMinimumValue').value,

            require_autoassignable:
                $('autoPickRequireAutoassignable').checked
        }
    };

    try {
        const csrfToken =
    document.querySelector('[name=csrfmiddlewaretoken]')?.value;

const response = await fetch(
    '/api/preferences/update',
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
    }
);
        const data = await response.json();

        if (!response.ok) {
            throw Error(
                data.error || 'Unable to save settings.'
            );
        }

        preferences = data;

        $('monitoringStatus').textContent =
            payload.monitoring.enabled
                ? 'MONITORING ACTIVE'
                : 'MONITORING PAUSED';

        showSettingsMessage(
            'Settings saved successfully.'
        );

        await loadPreferences();
        await refresh();

        setTimeout(closeSettings, 800);

    } catch (error) {

        showSettingsMessage(
            error.message || 'Unable to save settings.',
            true
        );

    } finally {

        button.disabled = false;
        button.textContent = 'Save settings';
    }
}

function showSettingsMessage(message, error = false) {
    const box = $('settingsMessage');

    box.hidden = false;
    box.textContent = message;

    box.classList.toggle('error-message', error);
}


/* =========================
   EVENT HANDLERS
========================= */

$('refresh').onclick = refresh;

$('query').oninput = render;

$('site').onchange = render;

$('auto').onclick = () => {
    onlyAuto = !onlyAuto;

    $('auto').classList.toggle(
        'active',
        onlyAuto
    );

    render();
};


/* Settings buttons */

$('settings').onclick = openSettings;

$('settingsToolbar').onclick = openSettings;

$('closeSettings').onclick = closeSettings;

$('cancelSettings').onclick = closeSettings;

$('saveSettings').onclick = saveSettings;

$('autoPickEnabled').onchange =
    updateAutoPickStatus;


/* Close drawer when clicking outside panel */

$('settingsOverlay').onclick = event => {
    if (event.target === $('settingsOverlay')) {
        closeSettings();
    }
};


async function initializeDashboard() {
    await loadPreferences();
    fillSites();
    render();
    await refresh();
}

initializeDashboard();
async function setupPushNotifications() {
    if (!("serviceWorker" in navigator)) {
        console.warn("Service workers are not supported.");
        return;
    }

    if (!("PushManager" in window)) {
        console.warn("Push notifications are not supported.");
        return;
    }

    try {
        const registration = await navigator.serviceWorker.register(
            "/static/shifthunter/sw.js"
        );

        let permission = Notification.permission;

        if (permission === "default") {
            permission = await Notification.requestPermission();
        }

        if (permission !== "granted") {
            console.warn("Notification permission was not granted.");
            return;
        }

        const vapidPublicKey =
            document
                .querySelector('meta[name="vapid-public-key"]')
                .getAttribute("content");

        const existingSubscription =
            await registration.pushManager.getSubscription();

        const subscription =
            existingSubscription ||
            await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(
                    vapidPublicKey
                ),
            });

        const response = await fetch(
            "/api/push/subscribe",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify(subscription),
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.error || "Failed to save push subscription."
            );
        }

        console.log(
            "Push subscription registered:",
            result
        );
    } catch (error) {
        console.error(
            "Push notification setup failed:",
            error
        );
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat(
        (4 - (base64String.length % 4)) % 4
    );

    const base64 = (
        base64String + padding
    )
        .replace(/-/g, "+")
        .replace(/_/g, "/");

    const rawData = window.atob(base64);

    return Uint8Array.from(
        [...rawData].map(
            (char) => char.charCodeAt(0)
        )
    );
}

function getCookie(name) {
    const cookies = document.cookie.split(";");

    for (const cookie of cookies) {
        const [key, value] = cookie.trim().split("=");

        if (key === name) {
            return decodeURIComponent(value);
        }
    }

    return null;
}

document.addEventListener(
    "DOMContentLoaded",
    () => {
        setupPushNotifications();
    }
);
