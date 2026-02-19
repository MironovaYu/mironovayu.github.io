/**
 * Миронова — Психолог
 * Main JavaScript: theme toggle, mobile menu, scroll effects, animations
 */

(function () {
    'use strict';

    // ===== Theme Toggle =====
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;

    function getPreferredTheme() {
        const stored = localStorage.getItem('theme');
        if (stored) return stored;
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    // Initialize theme
    setTheme(getPreferredTheme());

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            setTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    // ===== Mobile Menu =====
    const burger = document.getElementById('burger');
    const mobileMenu = document.getElementById('mobileMenu');

    if (burger && mobileMenu) {
        burger.addEventListener('click', () => {
            burger.classList.toggle('burger--active');
            mobileMenu.classList.toggle('mobile-menu--open');
            document.body.style.overflow = mobileMenu.classList.contains('mobile-menu--open') ? 'hidden' : '';
        });

        // Close on link click
        mobileMenu.querySelectorAll('.mobile-menu__link').forEach(link => {
            link.addEventListener('click', () => {
                burger.classList.remove('burger--active');
                mobileMenu.classList.remove('mobile-menu--open');
                document.body.style.overflow = '';
            });
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!mobileMenu.contains(e.target) && !burger.contains(e.target)) {
                burger.classList.remove('burger--active');
                mobileMenu.classList.remove('mobile-menu--open');
                document.body.style.overflow = '';
            }
        });
    }

    // ===== Header Scroll Effect =====
    const header = document.getElementById('header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        if (header) {
            if (currentScroll > 10) {
                header.classList.add('header--scrolled');
            } else {
                header.classList.remove('header--scrolled');
            }
        }
        lastScroll = currentScroll;
    }, { passive: true });

    // ===== Scroll to Top Button =====
    const scrollTopBtn = document.createElement('button');
    scrollTopBtn.className = 'scroll-top';
    scrollTopBtn.setAttribute('aria-label', 'Наверх');
    scrollTopBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
    document.body.appendChild(scrollTopBtn);

    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 400) {
            scrollTopBtn.classList.add('scroll-top--visible');
        } else {
            scrollTopBtn.classList.remove('scroll-top--visible');
        }
    }, { passive: true });

    scrollTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // ===== Fade-in Animations =====
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in--visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });

    // ===== Smooth scroll for anchor links =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ===== Help Section Toggle (mobile) =====
    const helpToggle = document.getElementById('helpToggle');
    const helpList = document.getElementById('helpList');

    if (helpToggle && helpList) {
        helpToggle.addEventListener('click', () => {
            const isOpen = helpList.classList.toggle('help-list--open');
            helpToggle.setAttribute('aria-expanded', isOpen);
            helpToggle.querySelector('.help-toggle__text').textContent = isOpen ? 'Скрыть' : 'Ещё';
        });
    }

    // ===== Services Accordion =====
    document.querySelectorAll('.svc-card__header').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.svc-card');
            const isOpen = card.classList.toggle('svc-card--open');
            btn.setAttribute('aria-expanded', isOpen);
        });
    });

    // Auto-open service card if URL has hash
    if (window.location.hash) {
        const target = document.querySelector(window.location.hash);
        if (target && target.classList.contains('svc-card')) {
            target.classList.add('svc-card--open');
            const header = target.querySelector('.svc-card__header');
            if (header) header.setAttribute('aria-expanded', 'true');
            setTimeout(() => {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }

    // ===== Announcements Calendar =====
    const calGrid = document.getElementById('calGrid');
    const calMonth = document.getElementById('calMonth');
    const calPrev = document.getElementById('calPrev');
    const calNext = document.getElementById('calNext');
    const upcomingList = document.getElementById('upcomingList');

    if (calGrid && window.__announcements__) {
        const announcements = window.__announcements__;
        const MONTH_NAMES = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];
        const MONTH_NAMES_SHORT = [
            'янв', 'фев', 'мар', 'апр', 'май', 'июн',
            'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
        ];

        const now = new Date();
        let currentYear = now.getFullYear();
        let currentMonth = now.getMonth();

        function getEventsForDate(year, month, day) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            return announcements.filter(a => a.date === dateStr);
        }

        function renderCalendar(year, month) {
            calMonth.textContent = `${MONTH_NAMES[month]} ${year}`;

            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            // Monday = 0, Sunday = 6
            let startWeekday = firstDay.getDay() - 1;
            if (startWeekday < 0) startWeekday = 6;

            const daysInMonth = lastDay.getDate();
            const prevMonthLastDay = new Date(year, month, 0).getDate();

            const today = new Date();
            const todayYear = today.getFullYear();
            const todayMonth = today.getMonth();
            const todayDate = today.getDate();

            let html = '';

            // Days from previous month
            for (let i = startWeekday - 1; i >= 0; i--) {
                const day = prevMonthLastDay - i;
                html += `<div class="calendar__day calendar__day--other"><span class="calendar__day-num">${day}</span></div>`;
            }

            // Days of current month
            for (let d = 1; d <= daysInMonth; d++) {
                const events = getEventsForDate(year, month, d);
                const isToday = (year === todayYear && month === todayMonth && d === todayDate);
                let cls = 'calendar__day';
                if (isToday) cls += ' calendar__day--today';
                if (events.length) cls += ' calendar__day--has-event';

                let eventsHtml = '';
                if (events.length) {
                    eventsHtml = '<div class="calendar__events">';
                    events.forEach((ev, idx) => {
                        eventsHtml += `<span class="calendar__event-dot" data-ann-idx="${announcements.indexOf(ev)}">${ev.title}</span>`;
                    });
                    eventsHtml += '</div>';
                }

                html += `<div class="${cls}" data-day="${d}"><span class="calendar__day-num">${d}</span>${eventsHtml}</div>`;
            }

            // Days from next month
            const totalCells = startWeekday + daysInMonth;
            const remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
            for (let i = 1; i <= remaining; i++) {
                html += `<div class="calendar__day calendar__day--other"><span class="calendar__day-num">${i}</span></div>`;
            }

            calGrid.innerHTML = html;

            // Attach click handlers to event dots
            calGrid.querySelectorAll('.calendar__event-dot').forEach(dot => {
                dot.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const idx = parseInt(dot.getAttribute('data-ann-idx'));
                    openAnnModal(announcements[idx]);
                });
            });

            // Click on day cell with events
            calGrid.querySelectorAll('.calendar__day--has-event').forEach(cell => {
                cell.addEventListener('click', () => {
                    const day = parseInt(cell.getAttribute('data-day'));
                    const events = getEventsForDate(year, month, day);
                    if (events.length === 1) {
                        openAnnModal(events[0]);
                    } else if (events.length > 1) {
                        openAnnModal(events[0]);
                    }
                });
            });
        }

        function renderUpcoming() {
            if (!upcomingList) return;
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const upcoming = announcements
                .filter(a => {
                    const d = new Date(a.date + 'T00:00:00');
                    return d >= today;
                })
                .sort((a, b) => a.date.localeCompare(b.date))
                .slice(0, 5);

            if (!upcoming.length) {
                upcomingList.innerHTML = '';
                return;
            }

            let html = '<h3 class="announcements-upcoming__title">Ближайшие события</h3>';
            upcoming.forEach((ann, i) => {
                const d = new Date(ann.date + 'T00:00:00');
                const day = d.getDate();
                const monthShort = MONTH_NAMES_SHORT[d.getMonth()];

                let metaHtml = '';
                if (ann.time) {
                    metaHtml += `<span class="ann-upcoming-card__meta-item">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                        ${ann.time}
                    </span>`;
                }
                if (ann.location) {
                    metaHtml += `<span class="ann-upcoming-card__meta-item">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                        ${ann.location}
                    </span>`;
                }

                html += `<div class="ann-upcoming-card" data-ann-upcoming="${i}">
                    <div class="ann-upcoming-card__date">
                        <span class="ann-upcoming-card__date-day">${day}</span>
                        <span class="ann-upcoming-card__date-month">${monthShort}</span>
                    </div>
                    <div class="ann-upcoming-card__body">
                        <div class="ann-upcoming-card__title">${ann.title}</div>
                        <div class="ann-upcoming-card__meta">${metaHtml}</div>
                    </div>
                </div>`;
            });

            upcomingList.innerHTML = html;

            // Click handler for upcoming cards
            upcomingList.querySelectorAll('.ann-upcoming-card').forEach(card => {
                card.addEventListener('click', () => {
                    const idx = parseInt(card.getAttribute('data-ann-upcoming'));
                    openAnnModal(upcoming[idx]);
                });
            });
        }

        // Modal
        const modalOverlay = document.getElementById('annModalOverlay');
        const modalClose = document.getElementById('annModalClose');
        const modalTitle = document.getElementById('annModalTitle');
        const modalDate = document.getElementById('annModalDate');
        const modalTime = document.getElementById('annModalTime');
        const modalLocation = document.getElementById('annModalLocation');
        const modalDesc = document.getElementById('annModalDesc');
        const modalImage = document.getElementById('annModalImage');

        function formatDate(dateStr) {
            const d = new Date(dateStr + 'T00:00:00');
            const day = d.getDate();
            const month = MONTH_NAMES[d.getMonth()].toLowerCase();
            const year = d.getFullYear();
            return `${day} ${month} ${year}`;
        }

        function openAnnModal(ann) {
            modalTitle.textContent = ann.title;
            modalDate.querySelector('span').textContent = formatDate(ann.date);
            modalDate.style.display = 'flex';

            if (ann.time) {
                modalTime.querySelector('span').textContent = ann.time;
                modalTime.style.display = 'flex';
            } else {
                modalTime.style.display = 'none';
            }

            if (ann.location) {
                modalLocation.querySelector('span').textContent = ann.location;
                modalLocation.style.display = 'flex';
            } else {
                modalLocation.style.display = 'none';
            }

            modalDesc.innerHTML = ann.description || '';

            if (ann.image) {
                modalImage.innerHTML = `<img src="/static/${ann.image}" alt="${ann.title}">`;
                modalImage.classList.add('ann-modal__image--visible');
            } else {
                modalImage.innerHTML = '';
                modalImage.classList.remove('ann-modal__image--visible');
            }

            modalOverlay.classList.add('ann-modal-overlay--open');
            document.body.style.overflow = 'hidden';
        }

        function closeAnnModal() {
            modalOverlay.classList.remove('ann-modal-overlay--open');
            document.body.style.overflow = '';
        }

        if (modalClose) modalClose.addEventListener('click', closeAnnModal);
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) closeAnnModal();
            });
        }
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('ann-modal-overlay--open')) {
                closeAnnModal();
            }
        });

        // Navigation
        if (calPrev) calPrev.addEventListener('click', () => {
            currentMonth--;
            if (currentMonth < 0) { currentMonth = 11; currentYear--; }
            renderCalendar(currentYear, currentMonth);
        });

        if (calNext) calNext.addEventListener('click', () => {
            currentMonth++;
            if (currentMonth > 11) { currentMonth = 0; currentYear++; }
            renderCalendar(currentYear, currentMonth);
        });

        // Initial render
        renderCalendar(currentYear, currentMonth);
        renderUpcoming();
    }

})();
