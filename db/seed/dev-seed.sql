-- Dev seed data
-- Passwords/PINs are bcrypt hashes of 'admin123' or '1234'
-- Generated with: python -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())"

DO $$
DECLARE
    msp_tenant_id uuid;
    acme_tenant_id uuid;
    acme_admin_user_id uuid;
    acme_sales_user_id uuid;
    acme_user_user_id uuid;
    vm_100_id uuid;
    vm_101_id uuid;
    vm_102_id uuid;
    ext_100_id uuid;
    ext_101_id uuid;
    ext_102_id uuid;
    trunk_id uuid;
    did_main_id uuid;
    did_sales_id uuid;
    inbound_route_id uuid;
    outbound_route_id uuid;
    ring_group_id uuid;
    pin_hash text;
    sip_hash text;
BEGIN
    -- bcrypt hash of 'admin123' (password for users)
    -- bcrypt hash of '1234' (PIN for voicemail)
    pin_hash := '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476';
    sip_hash := '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476';

    -- ═══════════════════════════════════════════
    -- TENANTS
    -- ═══════════════════════════════════════════

    -- MSP platform tenant
    INSERT INTO tenants (id, name, slug, sip_domain, notes)
    VALUES (
        'a0000000-0000-0000-0000-000000000001',
        'MSP Platform',
        'msp',
        'msp.sip.local',
        'Platform management tenant'
    )
    ON CONFLICT (slug) DO UPDATE SET sip_domain = EXCLUDED.sip_domain
    RETURNING id INTO msp_tenant_id;

    IF msp_tenant_id IS NULL THEN
        SELECT id INTO msp_tenant_id FROM tenants WHERE slug = 'msp';
    END IF;

    -- Test tenant: Acme Corp
    INSERT INTO tenants (id, name, slug, sip_domain, notes)
    VALUES (
        'b0000000-0000-0000-0000-000000000002',
        'Acme Corp',
        'acme',
        'acme.sip.local',
        'Test tenant for development'
    )
    ON CONFLICT (slug) DO UPDATE SET sip_domain = EXCLUDED.sip_domain
    RETURNING id INTO acme_tenant_id;

    IF acme_tenant_id IS NULL THEN
        SELECT id INTO acme_tenant_id FROM tenants WHERE slug = 'acme';
    END IF;

    -- ═══════════════════════════════════════════
    -- USERS
    -- ═══════════════════════════════════════════

    -- MSP Super Admin user
    INSERT INTO users (tenant_id, email, password_hash, first_name, last_name, role)
    VALUES (
        msp_tenant_id,
        'admin@msp.local',
        '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476',
        'MSP',
        'Admin',
        'msp_super_admin'
    )
    ON CONFLICT (email) DO NOTHING;

    -- Acme Corp admin user
    INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, role)
    VALUES (
        'c0000000-0000-0000-0000-000000000001',
        acme_tenant_id,
        'admin@acme.local',
        '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476',
        'Acme',
        'Admin',
        'tenant_admin'
    )
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO acme_admin_user_id;

    IF acme_admin_user_id IS NULL THEN
        SELECT id INTO acme_admin_user_id FROM users WHERE email = 'admin@acme.local';
    END IF;

    -- Acme Corp sales manager
    INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, role)
    VALUES (
        'c0000000-0000-0000-0000-000000000002',
        acme_tenant_id,
        'sales@acme.local',
        '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476',
        'Sales',
        'Manager',
        'tenant_manager'
    )
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO acme_sales_user_id;

    IF acme_sales_user_id IS NULL THEN
        SELECT id INTO acme_sales_user_id FROM users WHERE email = 'sales@acme.local';
    END IF;

    -- Acme Corp regular user
    INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, role)
    VALUES (
        'c0000000-0000-0000-0000-000000000003',
        acme_tenant_id,
        'user@acme.local',
        '$2b$12$R4/oocGln3gYmx9B8ObiP.uT4Hk6v7UXf7X17e8gd58qxZmMFz476',
        'Regular',
        'User',
        'tenant_user'
    )
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO acme_user_user_id;

    IF acme_user_user_id IS NULL THEN
        SELECT id INTO acme_user_user_id FROM users WHERE email = 'user@acme.local';
    END IF;

    -- ═══════════════════════════════════════════
    -- VOICEMAIL BOXES
    -- ═══════════════════════════════════════════

    vm_100_id := 'd0000000-0000-0000-0000-000000000001';
    vm_101_id := 'd0000000-0000-0000-0000-000000000002';
    vm_102_id := 'd0000000-0000-0000-0000-000000000003';

    INSERT INTO voicemail_boxes (id, tenant_id, mailbox_number, pin_hash, greeting_type, email_notification, max_messages)
    VALUES
        (vm_100_id, acme_tenant_id, '100', pin_hash, 'default', true, 100),
        (vm_101_id, acme_tenant_id, '101', pin_hash, 'default', true, 100),
        (vm_102_id, acme_tenant_id, '102', pin_hash, 'default', true, 100)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- EXTENSIONS
    -- ═══════════════════════════════════════════

    ext_100_id := 'e0000000-0000-0000-0000-000000000001';
    ext_101_id := 'e0000000-0000-0000-0000-000000000002';
    ext_102_id := 'e0000000-0000-0000-0000-000000000003';

    INSERT INTO extensions (id, tenant_id, extension_number, sip_username, sip_password_hash, user_id, voicemail_box_id, internal_cid_name, internal_cid_number, class_of_service, recording_policy)
    VALUES
        (ext_100_id, acme_tenant_id, '100', 'b0000000-100', sip_hash, acme_admin_user_id, vm_100_id, 'Acme Admin', '100', 'international', 'always'),
        (ext_101_id, acme_tenant_id, '101', 'b0000000-101', sip_hash, acme_sales_user_id, vm_101_id, 'Sales Mgr', '101', 'domestic', 'on_demand'),
        (ext_102_id, acme_tenant_id, '102', 'b0000000-102', sip_hash, acme_user_user_id, vm_102_id, 'Regular User', '102', 'domestic', 'never')
    ON CONFLICT DO NOTHING;

    -- Update recording_policy on existing seeded extensions
    UPDATE extensions SET recording_policy = 'always' WHERE id = ext_100_id;
    UPDATE extensions SET recording_policy = 'on_demand' WHERE id = ext_101_id;
    UPDATE extensions SET recording_policy = 'never' WHERE id = ext_102_id;

    -- ═══════════════════════════════════════════
    -- SIP TRUNKS
    -- ═══════════════════════════════════════════

    trunk_id := 'f0000000-0000-0000-0000-000000000001';

    INSERT INTO sip_trunks (id, tenant_id, name, auth_type, host, port, username, max_channels, transport, inbound_cid_mode)
    VALUES (
        trunk_id,
        acme_tenant_id,
        'ClearlyIP Test Trunk',
        'registration',
        'sip.clearlyip.com',
        5061,
        'acme_trunk',
        30,
        'tls',
        'passthrough'
    )
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- DIDs
    -- ═══════════════════════════════════════════

    did_main_id := 'f1000000-0000-0000-0000-000000000001';
    did_sales_id := 'f1000000-0000-0000-0000-000000000002';

    INSERT INTO dids (id, tenant_id, number, provider, status)
    VALUES
        (did_main_id, acme_tenant_id, '+15551001000', 'clearlyip', 'active'),
        (did_sales_id, acme_tenant_id, '+15551001001', 'clearlyip', 'active')
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- INBOUND ROUTES
    -- ═══════════════════════════════════════════

    inbound_route_id := 'f2000000-0000-0000-0000-000000000001';

    INSERT INTO inbound_routes (id, tenant_id, name, did_id, destination_type, destination_id, enabled)
    VALUES (
        inbound_route_id,
        acme_tenant_id,
        'Main Number → Admin Ext',
        did_main_id,
        'extension',
        ext_100_id,
        true
    )
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- OUTBOUND ROUTES
    -- ═══════════════════════════════════════════

    outbound_route_id := 'f3000000-0000-0000-0000-000000000001';

    INSERT INTO outbound_routes (id, tenant_id, name, dial_pattern, strip_digits, cid_mode, priority, enabled)
    VALUES (
        outbound_route_id,
        acme_tenant_id,
        'US Domestic',
        '1NXXNXXXXXX',
        0,
        'extension',
        100,
        true
    )
    ON CONFLICT DO NOTHING;

    -- Trunk assignment for outbound route
    INSERT INTO outbound_route_trunks (outbound_route_id, trunk_id, position)
    VALUES (outbound_route_id, trunk_id, 0)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- RING GROUPS
    -- ═══════════════════════════════════════════

    ring_group_id := 'f4000000-0000-0000-0000-000000000001';

    INSERT INTO ring_groups (id, tenant_id, group_number, name, ring_strategy, ring_time, ring_time_per_member, skip_busy, cid_passthrough)
    VALUES (
        ring_group_id,
        acme_tenant_id,
        '*601',
        'Sales Team',
        'simultaneous',
        25,
        15,
        true,
        true
    )
    ON CONFLICT DO NOTHING;

    -- Ring group members (ext 100 + 101)
    INSERT INTO ring_group_members (ring_group_id, extension_id, position)
    VALUES
        (ring_group_id, ext_100_id, 0),
        (ring_group_id, ext_101_id, 1)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- CDRs (sample call detail records)
    -- ═══════════════════════════════════════════

    INSERT INTO call_detail_records (id, tenant_id, call_id, direction, caller_number, caller_name, called_number, extension_id, disposition, hangup_cause, duration_seconds, billable_seconds, ring_seconds, start_time, answer_time, end_time, has_recording)
    VALUES
        ('a1000000-0000-0000-0000-000000000001', acme_tenant_id, 'seed-call-001', 'inbound', '+15559991234', 'John Doe', '100', ext_100_id, 'answered', 'NORMAL_CLEARING', 120, 115, 5, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours' + INTERVAL '5 seconds', NOW() - INTERVAL '2 hours' + INTERVAL '120 seconds', true),
        ('a1000000-0000-0000-0000-000000000002', acme_tenant_id, 'seed-call-002', 'outbound', '101', 'Sales Mgr', '+15559995678', ext_101_id, 'answered', 'NORMAL_CLEARING', 300, 295, 5, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour' + INTERVAL '5 seconds', NOW() - INTERVAL '1 hour' + INTERVAL '300 seconds', false),
        ('a1000000-0000-0000-0000-000000000003', acme_tenant_id, 'seed-call-003', 'internal', '102', 'Regular User', '100', ext_102_id, 'no_answer', 'NO_ANSWER', 30, 0, 30, NOW() - INTERVAL '30 minutes', NULL, NOW() - INTERVAL '30 minutes' + INTERVAL '30 seconds', false)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- RECORDINGS (sample linked to first CDR)
    -- ═══════════════════════════════════════════

    INSERT INTO recordings (id, tenant_id, cdr_id, call_id, storage_path, storage_bucket, file_size_bytes, duration_seconds, format, sample_rate, sha256_hash, recording_policy)
    VALUES
        ('a2000000-0000-0000-0000-000000000001', acme_tenant_id, 'a1000000-0000-0000-0000-000000000001', 'seed-call-001', 'acme/seed-call-001.wav', 'recordings', 1920000, 115, 'wav', 8000, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'always')
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- AUDIO PROMPTS
    -- ═══════════════════════════════════════════

    INSERT INTO audio_prompts (id, tenant_id, name, description, category, file_size_bytes, duration_seconds, format, sample_rate, local_path)
    VALUES
        ('b1000000-0000-0000-0000-000000000001', acme_tenant_id, 'Main Greeting', 'Welcome to Acme Corp', 'ivr_greeting', 48000, 6, 'wav', 8000, '/recordings/prompts/acme/main-greeting.wav'),
        ('b1000000-0000-0000-0000-000000000002', acme_tenant_id, 'After Hours', 'Office is closed message', 'announcement', 32000, 4, 'wav', 8000, '/recordings/prompts/acme/after-hours.wav')
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- VOICEMAIL MESSAGES
    -- ═══════════════════════════════════════════

    INSERT INTO voicemail_messages (id, tenant_id, voicemail_box_id, caller_number, caller_name, duration_seconds, storage_path, storage_bucket, file_size_bytes, format, is_read, is_urgent, folder, call_id)
    VALUES
        ('b2000000-0000-0000-0000-000000000001', acme_tenant_id, vm_100_id, '+15559991234', 'John Doe', 15, 'acme/voicemail/100/seed-vm-001.wav', 'recordings', 120000, 'wav', false, false, 'new', 'seed-vm-call-001'),
        ('b2000000-0000-0000-0000-000000000002', acme_tenant_id, vm_100_id, '+15559995678', 'Jane Smith', 30, 'acme/voicemail/100/seed-vm-002.wav', 'recordings', 240000, 'wav', true, false, 'saved', 'seed-vm-call-002'),
        ('b2000000-0000-0000-0000-000000000003', acme_tenant_id, vm_101_id, '+15559991111', 'Bob Wilson', 8, 'acme/voicemail/101/seed-vm-003.wav', 'recordings', 64000, 'wav', false, true, 'new', 'seed-vm-call-003')
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- TIME CONDITIONS
    -- ═══════════════════════════════════════════

    INSERT INTO time_conditions (id, tenant_id, name, description, timezone, rules, match_destination_type, match_destination_id, nomatch_destination_type, nomatch_destination_id, enabled)
    VALUES
        ('b3000000-0000-0000-0000-000000000001', acme_tenant_id, 'Business Hours', 'Mon-Fri 8am-5pm EST', 'America/New_York',
         '[{"type": "day_of_week", "days": [1,2,3,4,5], "label": "Weekdays"}, {"type": "time_of_day", "start_time": "08:00", "end_time": "17:00", "label": "Business hours"}]'::jsonb,
         'extension', ext_100_id, 'voicemail', vm_100_id, true)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- IVR MENUS
    -- ═══════════════════════════════════════════

    INSERT INTO ivr_menus (id, tenant_id, name, description, greet_long_prompt_id, timeout, max_failures, max_timeouts, inter_digit_timeout, digit_len, enabled)
    VALUES
        ('b4000000-0000-0000-0000-000000000001', acme_tenant_id, 'Main Menu', 'Main auto-attendant', 'b1000000-0000-0000-0000-000000000001', 10, 3, 3, 2, 1, true)
    ON CONFLICT DO NOTHING;

    -- IVR menu options
    INSERT INTO ivr_menu_options (id, ivr_menu_id, digits, action_type, action_target_id, action_target_value, label, position)
    VALUES
        ('b5000000-0000-0000-0000-000000000001', 'b4000000-0000-0000-0000-000000000001', '1', 'extension', ext_100_id, '100', 'Press 1 for Admin', 0),
        ('b5000000-0000-0000-0000-000000000002', 'b4000000-0000-0000-0000-000000000001', '2', 'ring_group', ring_group_id, '*601', 'Press 2 for Sales', 1),
        ('b5000000-0000-0000-0000-000000000003', 'b4000000-0000-0000-0000-000000000001', '0', 'voicemail', vm_100_id, '100', 'Press 0 for Voicemail', 2),
        ('b5000000-0000-0000-0000-000000000004', 'b4000000-0000-0000-0000-000000000001', '*', 'repeat', NULL, NULL, 'Press * to repeat', 3)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- CALL QUEUES (ACD)
    -- ═══════════════════════════════════════════

    INSERT INTO queues (id, tenant_id, name, queue_number, description, strategy, max_wait_time, max_wait_time_with_no_agent, ring_timeout, wrapup_time, enabled)
    VALUES
        ('b6000000-0000-0000-0000-000000000001', acme_tenant_id, 'Sales Queue', '600', 'Sales team queue', 'longest-idle-agent', 300, 120, 30, 10, true)
    ON CONFLICT DO NOTHING;

    -- Queue members: ext 100 (level 1), ext 101 (level 1), ext 102 (level 2)
    INSERT INTO queue_members (id, queue_id, extension_id, level, position)
    VALUES
        ('b7000000-0000-0000-0000-000000000001', 'b6000000-0000-0000-0000-000000000001', ext_100_id, 1, 1),
        ('b7000000-0000-0000-0000-000000000002', 'b6000000-0000-0000-0000-000000000001', ext_101_id, 1, 2),
        ('b7000000-0000-0000-0000-000000000003', 'b6000000-0000-0000-0000-000000000001', ext_102_id, 2, 1)
    ON CONFLICT DO NOTHING;

    -- Set agent status on queue member extensions
    UPDATE extensions SET agent_status = 'Available' WHERE id IN (ext_100_id, ext_101_id);
    UPDATE extensions SET agent_status = 'Logged Out' WHERE id = ext_102_id;

    -- ═══════════════════════════════════════════
    -- CONFERENCE BRIDGES
    -- ═══════════════════════════════════════════

    INSERT INTO conference_bridges (id, tenant_id, name, room_number, description, max_participants, announce_join_leave, enabled)
    VALUES
        ('c8000000-0000-0000-0000-000000000001', acme_tenant_id, 'Main Conference', '800', 'Open conference room', 50, true, true)
    ON CONFLICT DO NOTHING;

    INSERT INTO conference_bridges (id, tenant_id, name, room_number, description, max_participants, participant_pin, moderator_pin, wait_for_moderator, announce_join_leave, enabled)
    VALUES
        ('c8000000-0000-0000-0000-000000000002', acme_tenant_id, 'Secure Conference', '801', 'PIN-protected conference', 25, '1234', '5678', true, true, true)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- PAGE GROUPS
    -- ═══════════════════════════════════════════

    INSERT INTO page_groups (id, tenant_id, name, page_number, description, page_mode, timeout)
    VALUES
        ('c9000000-0000-0000-0000-000000000001', acme_tenant_id, 'All Phones', '500', 'Page all phones', 'one_way', 60)
    ON CONFLICT DO NOTHING;

    -- Page group members: ext 100, 101, 102
    INSERT INTO page_group_members (id, page_group_id, extension_id, position)
    VALUES
        ('ca000000-0000-0000-0000-000000000001', 'c9000000-0000-0000-0000-000000000001', ext_100_id, 0),
        ('ca000000-0000-0000-0000-000000000002', 'c9000000-0000-0000-0000-000000000001', ext_101_id, 1),
        ('ca000000-0000-0000-0000-000000000003', 'c9000000-0000-0000-0000-000000000001', ext_102_id, 2)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- PICKUP GROUPS
    -- ═══════════════════════════════════════════

    UPDATE extensions SET pickup_group = '1' WHERE id IN (ext_100_id, ext_101_id);
    UPDATE extensions SET pickup_group = '2' WHERE id = ext_102_id;

    -- ═══════════════════════════════════════════
    -- FOLLOW ME
    -- ═══════════════════════════════════════════

    INSERT INTO follow_me (id, tenant_id, extension_id, enabled, strategy, ring_extension_first, extension_ring_time)
    VALUES (
        'cb000000-0000-0000-0000-000000000001',
        acme_tenant_id,
        ext_100_id,
        true,
        'sequential',
        true,
        20
    )
    ON CONFLICT DO NOTHING;

    INSERT INTO follow_me_destinations (id, follow_me_id, position, destination, ring_time)
    VALUES
        ('cc000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000001', 0, '+15559991234', 20),
        ('cc000000-0000-0000-0000-000000000002', 'cb000000-0000-0000-0000-000000000001', 1, '+15559995678', 15)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- MOH AUDIO PROMPT + TENANT DEFAULT
    -- ═══════════════════════════════════════════

    INSERT INTO audio_prompts (id, tenant_id, name, description, category, file_size_bytes, duration_seconds, format, sample_rate, local_path)
    VALUES
        ('b1000000-0000-0000-0000-000000000003', acme_tenant_id, 'Hold Music', 'Default hold music', 'moh', 960000, 120, 'wav', 8000, '/recordings/prompts/acme/hold-music.wav')
    ON CONFLICT DO NOTHING;

    -- Set tenant default MOH
    UPDATE tenants SET default_moh_prompt_id = 'b1000000-0000-0000-0000-000000000003' WHERE id = acme_tenant_id;

    -- ═══════════════════════════════════════════
    -- CALLER ID RULES
    -- ═══════════════════════════════════════════

    INSERT INTO caller_id_rules (id, tenant_id, name, rule_type, match_pattern, action, priority, notes)
    VALUES
        ('d1000000-0000-0000-0000-000000000001', acme_tenant_id, 'Block Anonymous', 'block', 'anonymous', 'reject', 100, 'Reject anonymous callers'),
        ('d1000000-0000-0000-0000-000000000002', acme_tenant_id, 'Block Spam Range', 'block', '+1555000', 'hangup', 50, 'Hang up on known spam range')
    ON CONFLICT DO NOTHING;

    INSERT INTO caller_id_rules (id, tenant_id, name, rule_type, match_pattern, action, destination_id, priority, notes)
    VALUES
        ('d1000000-0000-0000-0000-000000000003', acme_tenant_id, 'VIP Allow', 'allow', '+15559991234', 'allow', NULL, 200, 'Always allow VIP caller')
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- HOLIDAY CALENDARS
    -- ═══════════════════════════════════════════

    INSERT INTO holiday_calendars (id, tenant_id, name, description)
    VALUES
        ('d2000000-0000-0000-0000-000000000001', acme_tenant_id, 'US Federal Holidays 2026', 'Standard US federal holidays')
    ON CONFLICT DO NOTHING;

    INSERT INTO holiday_entries (id, calendar_id, name, date, recur_annually, all_day, start_time, end_time)
    VALUES
        ('d3000000-0000-0000-0000-000000000001', 'd2000000-0000-0000-0000-000000000001', 'New Year''s Day', '2026-01-01', true, true, NULL, NULL),
        ('d3000000-0000-0000-0000-000000000002', 'd2000000-0000-0000-0000-000000000001', 'Independence Day', '2026-07-04', true, true, NULL, NULL),
        ('d3000000-0000-0000-0000-000000000003', 'd2000000-0000-0000-0000-000000000001', 'Thanksgiving', '2026-11-26', false, true, NULL, NULL),
        ('d3000000-0000-0000-0000-000000000004', 'd2000000-0000-0000-0000-000000000001', 'Christmas Day', '2026-12-25', true, true, NULL, NULL),
        ('d3000000-0000-0000-0000-000000000005', 'd2000000-0000-0000-0000-000000000001', 'Christmas Eve Afternoon', '2026-12-24', true, false, '12:00', '23:59')
    ON CONFLICT DO NOTHING;

    -- Link holiday calendar to Business Hours time condition
    UPDATE time_conditions SET holiday_calendar_id = 'd2000000-0000-0000-0000-000000000001' WHERE id = 'b3000000-0000-0000-0000-000000000001';

    -- ═══════════════════════════════════════════
    -- PHONE MODELS (global reference data)
    -- ═══════════════════════════════════════════

    INSERT INTO phone_models (id, manufacturer, model_name, model_family, max_line_keys, max_expansion_keys, max_expansion_modules, has_color_screen, has_wifi, has_bluetooth, has_expansion_port, has_poe, has_gigabit)
    VALUES
        ('f5000000-0000-0000-0000-000000000001', 'Yealink', 'T58W', 'yealink_t5x', 27, 40, 3, true, true, true, true, true, true),
        ('f5000000-0000-0000-0000-000000000002', 'Yealink', 'T54W', 'yealink_t5x', 27, 40, 3, true, true, true, true, true, true),
        ('f5000000-0000-0000-0000-000000000003', 'Yealink', 'T53W', 'yealink_t5x', 21, 40, 3, true, true, false, true, true, true),
        ('f5000000-0000-0000-0000-000000000004', 'Yealink', 'T46U', 'yealink_t4x', 27, 40, 3, true, false, false, true, true, true),
        ('f5000000-0000-0000-0000-000000000005', 'Yealink', 'T43U', 'yealink_t4x', 21, 40, 3, false, false, false, true, true, true),
        ('f5000000-0000-0000-0000-000000000006', 'Yealink', 'T33G', 'yealink_t3x', 12, 0, 0, true, false, false, false, true, true),
        ('f5000000-0000-0000-0000-000000000007', 'Yealink', 'T31G', 'yealink_t3x', 2, 0, 0, false, false, false, false, true, true),
        ('f5000000-0000-0000-0000-000000000008', 'Yealink', 'T31P', 'yealink_t3x', 2, 0, 0, false, false, false, false, true, false)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- DEVICES (sample device for Acme)
    -- ═══════════════════════════════════════════

    INSERT INTO devices (id, tenant_id, mac_address, phone_model_id, extension_id, name, location)
    VALUES
        ('f6000000-0000-0000-0000-000000000001', acme_tenant_id, '001565abcdef', 'f5000000-0000-0000-0000-000000000004', ext_100_id, 'Admin Desk Phone', 'Front Office')
    ON CONFLICT DO NOTHING;

    -- Sample BLF keys for the device
    INSERT INTO device_keys (id, tenant_id, device_id, key_section, key_index, key_type, label, value, line)
    VALUES
        ('f7000000-0000-0000-0000-000000000001', acme_tenant_id, 'f6000000-0000-0000-0000-000000000001', 'line_key', 1, 'line', 'Line 1', '100', 1),
        ('f7000000-0000-0000-0000-000000000002', acme_tenant_id, 'f6000000-0000-0000-0000-000000000001', 'line_key', 2, 'blf', 'Sales Mgr', '101', 1),
        ('f7000000-0000-0000-0000-000000000003', acme_tenant_id, 'f6000000-0000-0000-0000-000000000001', 'line_key', 3, 'blf', 'User', '102', 1),
        ('f7000000-0000-0000-0000-000000000004', acme_tenant_id, 'f6000000-0000-0000-0000-000000000001', 'line_key', 4, 'speed_dial', 'Support', '+18005551234', 1),
        ('f7000000-0000-0000-0000-000000000005', acme_tenant_id, 'f6000000-0000-0000-0000-000000000001', 'line_key', 5, 'park', 'Park 1', '70', 1)
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- AUDIT LOGS (sample entry)
    -- ═══════════════════════════════════════════

    INSERT INTO audit_logs (id, user_id, tenant_id, action, resource_type, ip_address, user_agent)
    VALUES (
        'cd000000-0000-0000-0000-000000000001',
        acme_admin_user_id,
        acme_tenant_id,
        'login',
        'auth',
        '127.0.0.1',
        'Mozilla/5.0 (seed data)'
    )
    ON CONFLICT DO NOTHING;

    -- ═══════════════════════════════════════════
    -- SMS PROVIDER CONFIG (ClearlyIP dummy)
    -- ═══════════════════════════════════════════

    INSERT INTO sms_provider_configs (id, tenant_id, provider_type, label, encrypted_credentials, is_default, is_active)
    VALUES (
        'e1000000-0000-0000-0000-000000000001',
        acme_tenant_id,
        'clearlyip',
        'ClearlyIP Production',
        'DUMMY_ENCRYPTED_CREDENTIALS',
        true,
        true
    )
    ON CONFLICT DO NOTHING;

    -- Enable SMS on the first Acme DID
    UPDATE dids SET sms_enabled = true WHERE tenant_id = acme_tenant_id AND number = '+15551001000';

    -- ═══════════════════════════════════════════
    -- SMS CONVERSATION + MESSAGES (sample)
    -- ═══════════════════════════════════════════

    INSERT INTO conversations (id, tenant_id, did_id, remote_number, channel, state, assigned_to_user_id, last_message_at)
    VALUES (
        'e2000000-0000-0000-0000-000000000001',
        acme_tenant_id,
        (SELECT id FROM dids WHERE number = '+15551001000' LIMIT 1),
        '+15559876543',
        'sms',
        'open',
        acme_admin_user_id,
        NOW() - INTERVAL '5 minutes'
    )
    ON CONFLICT DO NOTHING;

    INSERT INTO messages (id, conversation_id, tenant_id, direction, from_number, to_number, body, status, provider, segments)
    VALUES
        ('e3000000-0000-0000-0000-000000000001', 'e2000000-0000-0000-0000-000000000001', acme_tenant_id,
         'inbound', '+15559876543', '+15551001000', 'Hi, I need help with my account', 'received', 'clearlyip', 1),
        ('e3000000-0000-0000-0000-000000000002', 'e2000000-0000-0000-0000-000000000001', acme_tenant_id,
         'outbound', '+15551001000', '+15559876543', 'Sure! What is your account number?', 'delivered', 'clearlyip', 1),
        ('e3000000-0000-0000-0000-000000000003', 'e2000000-0000-0000-0000-000000000001', acme_tenant_id,
         'inbound', '+15559876543', '+15551001000', 'It is AC-12345', 'received', 'clearlyip', 1)
    ON CONFLICT DO NOTHING;

END $$;
