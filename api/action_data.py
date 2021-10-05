from betting.choices import A_MATCH_LOCK, A_MATCH_HIDE, A_MATCH_GO_LIVE, A_MATCH_END_NOW, A_QUESTION_LOCK, \
    A_QUESTION_HIDE, A_QUESTION_END_NOW, A_QUESTION_SELECT_WINNER, A_QUESTION_PAY, A_QUESTION_UN_PAY, A_QUESTION_REFUND

action_data = {
    # Match Actions
    A_MATCH_LOCK: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'lock_match(data.get("match_id"))',
    },
    A_MATCH_HIDE: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'hide_match(data.get("match_id"))',
    },
    A_MATCH_GO_LIVE: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'go_live_match(data.get("match_id"))',
    },
    A_MATCH_END_NOW: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'end_match_now(data.get("match_id"))',
    },
    # Question Actions
    A_QUESTION_LOCK: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'lock_question(data.get("question_id"))',
    },
    A_QUESTION_HIDE: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'hide_question(data.get("question_id"))',
    },
    A_QUESTION_END_NOW: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'end_question_now(data.get("question_id"))',
    },
    A_QUESTION_SELECT_WINNER: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'select_question_winner(data.get("question_id"), data.get("option_id"))',
    },
    A_QUESTION_PAY: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'pay_question(data.get("question_id"))',
    },
    A_QUESTION_UN_PAY: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'un_pay_question(data.get("question_id"))',
    },
    A_QUESTION_REFUND: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'refund_question(data.get("question_id"))',
    }
}
