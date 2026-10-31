
    let activeCustomerType = 'guest';
    let loadedHalls = [];
    let allHallStatuses = [];
    let selectedHallPrice = 0;
    let eventCalendarPicker = null;

    const hallStatusMeta = {
        available: { badge: 'badge-success', border: '#10b981', summaryClass: 'text-success' },
        booked: { badge: 'badge-danger', border: '#ef4444', summaryClass: 'text-danger' },
        ongoing: { badge: 'badge-warning', border: '#f59e0b', summaryClass: 'text-warning' },
        cleaning: { badge: 'badge-info', border: '#06b6d4', summaryClass: 'text-info' },
        blocked: { badge: 'badge-secondary', border: '#64748b', summaryClass: 'text-secondary' }
    };

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function toYMD(dateObj) {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, '0');
        const d = String(dateObj.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    function formatRangeText(startDate, endDate) {
        if (!startDate || !endDate) return '';
        return `${startDate} to ${endDate}`;
    }

    function setEventDates(startDate, endDate, syncCalendar) {
        document.getElementById('startDate').value = startDate || '';
        document.getElementById('endDate').value = endDate || '';
        document.getElementById('eventDateCalendar').value = formatRangeText(startDate, endDate);

        if (syncCalendar && eventCalendarPicker) {
            if (startDate && endDate) {
                eventCalendarPicker.setDate([startDate, endDate], false);
            } else {
                eventCalendarPicker.clear();
            }
        }
    }

    function updateEventDurationText(days) {
        const safeDays = Number.isFinite(days) ? days : 0;
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;
        const timeText = startTime && endTime ? `, ${startTime} - ${endTime}` : '';
        document.getElementById('eventDurationText').innerText = `${safeDays} day${safeDays === 1 ? '' : 's'}${timeText}`;
    }

    function renderHallSummary(summary) {
        const container = document.getElementById('hallStatusSummary');
        if (!summary) {
            container.innerHTML = '<div class="col-12"><div class="text-muted small">Select event dates to load live hall status counters.</div></div>';
            return;
        }

        const items = [
            ['Total Available Halls', summary.available || 0, 'available'],
            ['Total Booked Halls', summary.booked || 0, 'booked'],
            ['Total Ongoing Events', summary.ongoing || 0, 'ongoing'],
            ['Total Under Cleaning', summary.cleaning || 0, 'cleaning'],
            ['Total Reserved/Blocked', summary.blocked || 0, 'blocked']
        ];

        container.innerHTML = items.map(([label, count, key]) => {
            const meta = hallStatusMeta[key];
            return `
                <div class="col-md-6 col-xl mb-2">
                    <div class="card shadow-sm h-100" style="border: 1px solid ${meta.border}; border-radius: 12px;">
                        <div class="card-body p-3">
                            <div class="small text-muted">${label}</div>
                            <div class="h4 mb-0 ${meta.summaryClass}">${count}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderHallCards(halls) {
        const container = document.getElementById('hallCards');
        const selectedId = document.getElementById('hallId').value;

        if (!halls.length) {
            container.innerHTML = `
                <div class="col-12">
                    <div class="text-muted small">No halls match the selected dates and guest count.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = halls.map((hall) => {
            const meta = hallStatusMeta[hall.status_key] || hallStatusMeta.blocked;
            const isSelected = String(selectedId) === String(hall.hall_id);
            const actionClass = hall.selectable ? (isSelected ? 'btn-success' : 'btn-outline-success') : 'btn-light';
            const actionText = hall.selectable ? (isSelected ? 'Selected' : 'Select Hall') : 'Unavailable';

            return `
                <div class="col-md-6 col-xl-4 mb-3">
                    <div class="card shadow-sm h-100" style="border-radius: 12px; border: 1px solid #e2e8f0; border-left: 4px solid ${meta.border};">
                        <div class="card-body d-flex flex-column">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <div class="font-weight-bold text-dark">${escapeHtml(hall.hall_name)}</div>
                                    <div class="text-muted small">Hall No: ${escapeHtml(hall.hall_number)}</div>
                                </div>
                                <span class="badge ${meta.badge}">${escapeHtml(hall.status_label)}</span>
                            </div>
                            <div class="small text-muted mb-1">Supported event type: <span class="text-dark">${escapeHtml(hall.hall_type_display)}</span></div>
                            <div class="small text-muted mb-1">Capacity: <span class="text-dark">Up to ${escapeHtml(hall.hall_capacity)} guests</span></div>
                            <div class="small text-muted mb-1">Price: <span class="text-dark">$${Number(hall.hall_price || 0).toFixed(2)} / day</span></div>
                            <div class="small text-muted mb-3">Current status: <span class="text-dark">${escapeHtml(hall.current_status)}</span></div>
                            <button type="button" class="btn ${actionClass} btn-sm mt-auto" onclick="selectHallFromCard('${hall.hall_id}')" ${hall.selectable ? '' : 'disabled'}>
                                ${actionText}
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function populateHallSelect(halls, preferredHallId) {
        const hallSelect = document.getElementById('hallId');
        const availableHalls = halls || [];

        if (!availableHalls.length) {
            hallSelect.disabled = true;
            hallSelect.innerHTML = '<option value="">-- No available halls found --</option>';
            return;
        }

        hallSelect.disabled = false;
        hallSelect.innerHTML = '<option value="">-- Choose a Hall --</option>';
        availableHalls.forEach((hall) => {
            const opt = document.createElement('option');
            opt.value = hall.hall_id;
            opt.innerText = `${hall.hall_name} (${hall.hall_type_display}) - Max ${hall.hall_capacity} Guests - $${Number(hall.hall_price || 0).toFixed(2)}/day`;
            hallSelect.appendChild(opt);
        });

        if (preferredHallId && availableHalls.some((hall) => String(hall.hall_id) === String(preferredHallId))) {
            hallSelect.value = preferredHallId;
            const selectedHall = availableHalls.find((hall) => String(hall.hall_id) === String(preferredHallId));
            if (selectedHall) {
                const gcInput = document.getElementById('guestCount');
                const gcValue = parseInt(gcInput.value) || 0;
                if (gcValue > selectedHall.hall_capacity) {
                    gcInput.value = selectedHall.hall_capacity;
                }
            }
        }
    }

    function resetHallAvailability(message) {
        loadedHalls = [];
        allHallStatuses = [];
        selectedHallPrice = 0;
        renderHallSummary(null);
        document.getElementById('hallId').innerHTML = `<option value="">${message || '-- Choose dates to check available halls --'}</option>`;
        document.getElementById('hallId').disabled = true;
        document.getElementById('hallCards').innerHTML = `
            <div class="col-12">
                <div class="text-muted small">${message || 'Select event dates and guest count from the calendar to view hall availability.'}</div>
            </div>
        `;
        filterPackagesForHall('');
        updateEventDurationText(0);
        updateBillingSummary();
    }

    function initializeEventCalendar() {
        eventCalendarPicker = flatpickr('#eventDateCalendar', {
            inline: true,
            mode: 'range',
            minDate: 'today',
            dateFormat: 'Y-m-d',
            clickOpens: false,
            allowInput: false,
            onChange: function(selectedDates) {
                if (selectedDates.length >= 1) {
                    const orderedDates = selectedDates.slice().sort((a, b) => a - b);
                    const startDate = toYMD(orderedDates[0]);
                    const endDate = selectedDates.length === 2 ? toYMD(orderedDates[1]) : startDate;
                    setEventDates(startDate, endDate, false);
                    if (selectedDates.length === 2 || selectedDates.length === 1) {
                        checkHallAvailability();
                    }
                } else if (selectedDates.length === 0) {
                    setEventDates('', '', false);
                    resetHallAvailability('Select event dates and guest count from the calendar to view hall availability.');
                }
            }
        });
    }

    function resetEventSelection() {
        setEventDates('', '', true);
        resetHallAvailability('Select event dates and guest count from the calendar to view hall availability.');
    }

    function setCustomerType(type) {
        activeCustomerType = type;
        document.getElementById('customerType').value = type;
        
        const btnGuest = document.getElementById('btnGuestType');
        const btnReg = document.getElementById('btnRegisteredType');
        const secGuest = document.getElementById('guestCustomerSection');
        const secReg = document.getElementById('registeredCustomerSection');
        
        if (type === 'guest') {
            btnGuest.className = "btn btn-success btn-toggle-custom";
            btnReg.className = "btn btn-outline-secondary btn-toggle-custom";
            secGuest.style.display = "block";
            secReg.style.display = "none";
            document.getElementById('guestName').required = true;
            document.getElementById('guestPhone').required = true;
            document.getElementById('customerId').value = '';
            document.getElementById('redeemPoints').value = 0;
        } else {
            btnGuest.className = "btn btn-outline-secondary btn-toggle-custom";
            btnReg.className = "btn btn-success btn-toggle-custom";
            secGuest.style.display = "none";
            secReg.style.display = "block";
            document.getElementById('guestName').required = false;
            document.getElementById('guestPhone').required = false;
        }
        updateBillingSummary();
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById('guestName').required = true;
        document.getElementById('guestPhone').required = true;
        initializeEventCalendar();
        resetHallAvailability('Select event dates and guest count from the calendar to view hall availability.');
        
        const urlParams = new URLSearchParams(window.location.search);
        const urlHallId = urlParams.get('hall_id');
        const startDate = urlParams.get('date');
        const endDate = urlParams.get('end_date') || startDate;

        if (startDate && urlHallId) {
            window.initialHallId = urlHallId;
            setEventDates(startDate, endDate, true);
            checkHallAvailability();
        }

        document.getElementById('offlineEventForm').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
                e.preventDefault();
            }
        });
    });

    function searchCustomer() {
        const phoneInput = document.getElementById('searchPhone').value.trim();
        const detailsCard = document.getElementById('customerDetailsCard');
        const errorMsg = document.getElementById('customerSearchError');

        if (!phoneInput) {
            alert('Please enter a phone number to search.');
            return;
        }

        fetch("{% url 'api_search_customer' %}?phone=" + encodeURIComponent(phoneInput))
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    errorMsg.style.display = 'none';
                    detailsCard.style.display = 'block';
                    document.getElementById('customerId').value = data.customer.id;
                    document.getElementById('custName').innerText = data.customer.name;
                    document.getElementById('custEmail').innerText = data.customer.email || 'N/A';
                    
                    const memBadge = document.getElementById('custMembership');
                    memBadge.innerText = data.customer.membership_status;
                    if (data.customer.membership_status === 'Bronze') memBadge.style.background = '#cd7f32';
                    else if (data.customer.membership_status === 'Silver') memBadge.style.background = '#c0c0c0';
                    else if (data.customer.membership_status === 'Gold') memBadge.style.background = '#ffd700';
                    else if (data.customer.membership_status === 'Platinum') memBadge.style.background = '#e5e4e2';
                    
                    document.getElementById('custPoints').innerText = data.customer.loyalty_points;
                    document.getElementById('redeemPoints').max = data.customer.loyalty_points;
                    document.getElementById('maxRedeemText').innerText = data.customer.loyalty_points;
                } else {
                    detailsCard.style.display = 'none';
                    errorMsg.style.display = 'block';
                    document.getElementById('customerId').value = '';
                }
                updateBillingSummary();
            })
            .catch(err => {
                console.error(err);
                alert('An error occurred during customer search.');
            });
    }

    function checkHallAvailability() {
        const start = document.getElementById('startDate').value;
        const end = document.getElementById('endDate').value;
        const guestCount = document.getElementById('guestCount').value || '1';
        const startTime = document.getElementById('startTime').value || '';
        const endTime = document.getElementById('endTime').value || '';
        const hallSelect = document.getElementById('hallId');
        const loader = document.getElementById('hallLoader');
        let previousSelection = hallSelect.value;
        let reqHallId = '';
        if (window.initialHallId) {
            previousSelection = window.initialHallId;
            reqHallId = window.initialHallId;
            window.initialHallId = null;
        }

        if (!start || !end) {
            resetHallAvailability('Select event dates and guest count from the calendar to view hall availability.');
            return;
        }

        if (new Date(start) > new Date(end)) {
            alert('Start date cannot be after end date.');
            return;
        }

        loader.style.display = 'block';
        hallSelect.disabled = true;
        hallSelect.innerHTML = '<option value="">-- Loading available halls... --</option>';

        let url = "{% url 'api_available_halls' %}" +
            "?start_date=" + encodeURIComponent(start) +
            "&end_date=" + encodeURIComponent(end) +
            "&guest_count=" + encodeURIComponent(guestCount) +
            "&start_time=" + encodeURIComponent(startTime) +
            "&end_time=" + encodeURIComponent(endTime);
        if (reqHallId) {
            url += "&requested_hall_id=" + encodeURIComponent(reqHallId);
        }

        fetch(url)
            .then(res => res.json())
            .then(data => {
                loader.style.display = 'none';

                if (!data.success) {
                    loadedHalls = [];
                    allHallStatuses = [];
                    populateHallSelect([], '');
                    renderHallSummary(null);
                    renderHallCards([]);
                    filterPackagesForHall('');
                    updateEventDurationText(0);
                    updateBillingSummary();
                    return;
                }

                loadedHalls = data.halls || [];
                allHallStatuses = data.all_halls || [];
                renderHallSummary(data.summary || {});
                renderHallCards(allHallStatuses);
                populateHallSelect(loadedHalls, previousSelection);
                updateEventDurationText(data.event_days || 0);
                onHallSelected();
            })
            .catch(err => {
                console.error(err);
                loader.style.display = 'none';
                loadedHalls = [];
                allHallStatuses = [];
                hallSelect.disabled = true;
                hallSelect.innerHTML = '<option value="">-- Error loading halls --</option>';
                renderHallSummary(null);
                renderHallCards([]);
                filterPackagesForHall('');
                updateEventDurationText(0);
                updateBillingSummary();
            });
    }

    function filterPackagesForHall(hallId) {
        const packageSelect = document.getElementById('packageId');
        packageSelect.value = '';
        packageSelect.disabled = !hallId;
        packageSelect.options[0].text = hallId
            ? '-- None / Hall Only --'
            : '-- Select a hall first / No package --';

        Array.from(packageSelect.options).slice(1).forEach(option => {
            const matchesHall = option.dataset.hallId === String(hallId);
            option.hidden = !matchesHall;
            option.disabled = !matchesHall;
        });
    }

    function selectHallFromCard(hallId) {
        const hall = allHallStatuses.find((item) => String(item.hall_id) === String(hallId));
        if (!hall || !hall.selectable) {
            return;
        }
        document.getElementById('hallId').value = hallId;
        onHallSelected();
    }

    function onHallSelected() {
        const selectedId = document.getElementById('hallId').value;
        if (!selectedId) {
            selectedHallPrice = 0;
        } else {
            const hallObj = loadedHalls.find(h => String(h.hall_id) === String(selectedId));
            selectedHallPrice = hallObj ? Number(hallObj.hall_price || 0) : 0;
        }
        renderHallCards(allHallStatuses);
        filterPackagesForHall(selectedId);
        updateBillingSummary();
    }

    function updateBillingSummary() {
        const startVal = document.getElementById('startDate').value;
        const endVal = document.getElementById('endDate').value;
        let days = 0;
        
        if (startVal && endVal) {
            const diffTime = new Date(endVal) - new Date(startVal);
            days = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1);
        }
        document.getElementById('eventDays').innerText = days;
        updateEventDurationText(days);

        const hallCost = selectedHallPrice * days;
        document.getElementById('summaryHallPrice').innerText = `$${hallCost.toFixed(2)}`;

        const packageSelect = document.getElementById('packageId');
        const selectedPkg = packageSelect.options[packageSelect.selectedIndex];
        const packageCost = parseFloat(selectedPkg ? (selectedPkg.getAttribute('data-price') || '0') : '0');
        document.getElementById('summaryPackagePrice').innerText = `$${packageCost.toFixed(2)}`;

        const subtotal = hallCost + packageCost;
        let pointsDiscount = 0;
        const redeemInput = document.getElementById('redeemPoints');
        const pointsRow = document.getElementById('summaryRedeemRow');
        
        if (activeCustomerType === 'registered') {
            let pts = parseInt(redeemInput.value || '0');
            const maxPts = parseInt(redeemInput.max || '0');
            
            if (pts < 0) pts = 0;
            if (pts > maxPts) pts = maxPts;
            if (pts > subtotal) pts = Math.floor(subtotal);
            
            redeemInput.value = pts;
            pointsDiscount = pts;
            
            if (pointsDiscount > 0) {
                pointsRow.setAttribute('style', 'display: flex !important;');
                document.getElementById('summaryRedeemPrice').innerText = `-$${pointsDiscount.toFixed(2)}`;
            } else {
                pointsRow.setAttribute('style', 'display: none !important;');
            }
        } else {
            pointsRow.setAttribute('style', 'display: none !important;');
        }

        const grandTotal = Math.max(0, subtotal - pointsDiscount);
        document.getElementById('summaryTotalPrice').innerText = `$${grandTotal.toFixed(2)}`;

        const advanceInput = document.getElementById('advanceAmount');
        const paymentMethod = document.getElementById('paymentMethod').value;
        if (paymentMethod === 'Razorpay') {
            advanceInput.value = (grandTotal * 0.25).toFixed(2);
            advanceInput.readOnly = true;
        } else {
            advanceInput.readOnly = false;
        }
        let advance = parseFloat(advanceInput.value || '0');
        if (advance < 0) advance = 0;
        document.getElementById('summaryAdvancePrice').innerText = `$${advance.toFixed(2)}`;

        const pending = Math.max(0, grandTotal - advance);
        document.getElementById('summaryPendingPrice').innerText = `$${pending.toFixed(2)}`;
    }

    document.getElementById('offlineEventForm').addEventListener('submit', function(e) {
        e.preventDefault();

        // ---- VALIDATION CHECKS ----
        const form = this;
        const customerType = document.getElementById('customerType').value;
        const customerId = document.getElementById('customerId').value;
        const nameInput = document.getElementById('guestName');
        const phoneInput = document.getElementById('guestPhone');
        const emailInput = document.getElementById('guestEmail');
        const hallSelect = document.getElementById('hallId');
        const hallIdVal = hallSelect ? hallSelect.value : '';
        const startDateVal = document.getElementById('startDate').value;
        const endDateVal = document.getElementById('endDate').value;
        const guestCountVal = parseInt(document.getElementById('guestCount').value) || 0;
        const paymentMethod = document.getElementById('paymentMethod').value;

        let isValid = true;
        let errorMessages = [];

        // Clear previous error styling
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
            el.style.borderColor = '';
            el.style.color = '';
            const container = el.closest('.mb-3, .form-group, .col-md-6, .col-md-4');
            const label = container ? container.querySelector('label') : null;
            if (label) label.style.color = '';
        });

        // 1. Customer validation
        if (customerType === 'registered') {
            if (!customerId) {
                isValid = false;
                errorMessages.push("Please search and verify a registered customer profile.");
                const searchInput = document.getElementById('searchPhone');
                if (searchInput) { searchInput.classList.add('is-invalid'); searchInput.style.borderColor = 'red'; }
            }
        } else {
            if (nameInput && !nameInput.value.trim()) {
                isValid = false;
                errorMessages.push("Guest Name is required.");
                nameInput.classList.add('is-invalid'); nameInput.style.borderColor = 'red';
            }
            if (phoneInput && !phoneInput.value.match(/^\d{10}$/)) {
                isValid = false;
                errorMessages.push("Enter a valid 10-digit Guest phone number.");
                phoneInput.classList.add('is-invalid'); phoneInput.style.borderColor = 'red';
            }
            if (emailInput && emailInput.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
                isValid = false;
                errorMessages.push("Enter a valid Guest email address.");
                emailInput.classList.add('is-invalid'); emailInput.style.borderColor = 'red';
            }
        }

        // 2. Event dates
        if (!startDateVal || !endDateVal) {
            isValid = false;
            errorMessages.push("Start and End dates are required.");
            const dateCal = document.getElementById('eventDateCalendar');
            if (dateCal) { dateCal.classList.add('is-invalid'); dateCal.style.borderColor = 'red'; }
        } else {
            const todayStr = new Date().toISOString().split('T')[0];
            if (startDateVal < todayStr) {
                isValid = false;
                errorMessages.push("Start date cannot be in the past.");
            }
            if (startDateVal > endDateVal) {
                isValid = false;
                errorMessages.push("Start date cannot be after End date.");
            }
        }

        // 3. Hall selection
        if (!hallIdVal) {
            isValid = false;
            errorMessages.push("Please select an available hall.");
            if (hallSelect) { hallSelect.classList.add('is-invalid'); hallSelect.style.borderColor = 'red'; }
        }

        // 4. Guest count
        if (guestCountVal < 1) {
            isValid = false;
            errorMessages.push("Expected guest count must be at least 1.");
            const gc = document.getElementById('guestCount');
            if (gc) { gc.classList.add('is-invalid'); gc.style.borderColor = 'red'; }
        }

        if (!isValid) {
            Swal.fire({
                icon: 'error',
                title: 'Validation Error',
                html: "<ul style='text-align:left; font-size:14px; color:#1c1d1f;'><li>" + errorMessages.join("</li><li>") + "</li></ul>",
                confirmButtonText: 'OK',
                customClass: { popup: 'stayzen-swal-popup', title: 'stayzen-swal-title', confirmButton: 'stayzen-swal-confirm' },
                buttonsStyling: false
            });
            return;
        }
        // ---- END VALIDATION ----

        // For Cash payments, submit natively
        if (paymentMethod !== 'Razorpay') {
            form.submit();
            return;
        }
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin mr-2"></i>Processing...';
        
        const formData = new FormData(this);
        formData.append('ajax', '1');
        
        fetch(this.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.razorpay) {
                const ctx = data.context;
                const options = {
                    key: ctx.razorpay_key,
                    amount: (function() {

                    var amt = parseFloat(ctx.amount);

                    var key = ctx.razorpay_key;

                    if (key && key.indexOf("rzp_test") === 0 && amt > 50000) {

                    return 50000 * 100;

                    }

                    return Math.round(amt * 100);

                    })(),
                    currency: "INR",
                    name: "StayZen",
                    description: "Offline Event Booking #" + ctx.booking_id,
                    prefill: {
                        name: ctx.name,
                        email: ctx.email,
                        contact: ctx.phone
                    },
                    handler: function(response) {
                        fetch("{% url 'razorpay_callback' %}", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRFToken": "{{ csrf_token }}"
                            },
                            body: JSON.stringify({
                                booking_id: ctx.booking_id,
                                booking_type: ctx.booking_type,
                                razorpay_payment_id: response.razorpay_payment_id
                            })
                        })
                        .then(res => res.json())
                        .then(cbData => {
                            if (cbData.success) {
                                Swal.fire({
                                    title: 'Payment Successful',
                                    text: cbData.details ? cbData.details.message : 'Offline event booking has been confirmed successfully!',
                                    icon: 'success',
                                    confirmButtonText: 'OK',
                                    customClass: {
                                        popup: 'stayzen-swal-popup',
                                        title: 'stayzen-swal-title',
                                        confirmButton: 'stayzen-swal-confirm'
                                    },
                                    buttonsStyling: false
                                }).then(() => {
                                    window.location.href = cbData.redirect_url || "{% url 'receptionist_hall_bookings' %}";
                                });
                            } else {
                                Swal.fire({
                                    title: 'Error',
                                    text: 'Payment confirmation failed: ' + cbData.message,
                                    icon: 'error',
                                    confirmButtonText: 'OK',
                                    customClass: {
                                        popup: 'stayzen-swal-popup',
                                        title: 'stayzen-swal-title',
                                        confirmButton: 'stayzen-swal-confirm'
                                    },
                                    buttonsStyling: false
                                });
                                submitBtn.disabled = false;
                                submitBtn.innerHTML = originalBtnHTML;
                            }
                        })
                        .catch(err => {
                            console.error(err);
                            Swal.fire({
                                title: 'Error',
                                text: 'Failed to verify payment with server.',
                                icon: 'error',
                                confirmButtonText: 'OK',
                                customClass: {
                                    popup: 'stayzen-swal-popup',
                                    title: 'stayzen-swal-title',
                                    confirmButton: 'stayzen-swal-confirm'
                                },
                                buttonsStyling: false
                            });
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalBtnHTML;
                        });
                    },
                    modal: {
                        ondismiss: function() {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalBtnHTML;
                        }
                    },
                    theme: {
                        color: "#10b981"
                    }
                };
                const rzp = new Razorpay(options);
                rzp.open();
            } else {
                Swal.fire({
                    title: 'Error',
                    text: data.message || 'Something went wrong while initiating event booking.',
                    icon: 'error',
                    confirmButtonText: 'OK',
                    customClass: {
                        popup: 'stayzen-swal-popup',
                        title: 'stayzen-swal-title',
                        confirmButton: 'stayzen-swal-confirm'
                    },
                    buttonsStyling: false
                });
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHTML;
            }
        })
        .catch(err => {
            console.error(err);
            Swal.fire({
                title: 'Error',
                text: 'An error occurred during booking creation.',
                icon: 'error',
                confirmButtonText: 'OK',
                customClass: {
                    popup: 'stayzen-swal-popup',
                    title: 'stayzen-swal-title',
                    confirmButton: 'stayzen-swal-confirm'
                },
                buttonsStyling: false
            });
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHTML;
    });

    // Live validation logic
    document.addEventListener('DOMContentLoaded', function() {
        const guestName = document.getElementById('guestName');
        const guestPhone = document.getElementById('guestPhone');
        const guestEmail = document.getElementById('guestEmail');

        function toggleError(input, condition) {
            const container = input.closest('.mb-3, .form-group, .col-md-6, .col-md-4, .zen-form-group');
            const label = container ? container.querySelector('label') : null;
            if (condition) {
                input.classList.add('is-invalid');
                input.style.borderColor = 'red';
                input.style.color = 'red';
                if (label) label.style.color = 'red';
            } else {
                input.classList.remove('is-invalid');
                input.style.borderColor = '';
                input.style.color = '';
                if (label) label.style.color = '';
            }
        }

        if (guestName) {
            guestName.addEventListener('input', function() {
                toggleError(this, this.value.trim() === '');
            });
        }

        if (guestPhone) {
            guestPhone.addEventListener('input', function() {
                toggleError(this, !this.value.match(/^\d{10}$/));
            });
        }

        if (guestEmail) {
            guestEmail.addEventListener('input', function() {
                toggleError(this, this.value.trim() !== '' && !this.value.includes('@'));
            });
        }
    });
