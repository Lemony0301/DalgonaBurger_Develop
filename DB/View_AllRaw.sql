SELECT id, stage, tokens, clear_time, created_at
        FROM run_logs
        ORDER BY created_at DESC
        LIMIT 20;