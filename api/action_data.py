from betting.choices import A_MATCH_LOCK, A_MATCH_HIDE, A_MATCH_GO_LIVE, A_MATCH_END_NOW, A_QUESTION_LOCK, \
    A_QUESTION_HIDE, A_QUESTION_END_NOW, A_QUESTION_SELECT_WINNER, A_QUESTION_UNSELECT_WINNER, \
    A_QUESTION_REFUND, A_MAKE_GAME_EDITOR, A_REMOVE_GAME_EDITOR, A_REFUND_BET, A_TRANSFER_ACCEPT, A_WITHDRAW_ACCEPT, \
    A_DEPOSIT_ACCEPT, A_DEPOSIT_CANCEL, A_WITHDRAW_CANCEL, A_TRANSFER_CANCEL

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
    A_QUESTION_UNSELECT_WINNER: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'unselect_question_winner(data.get("question_id"))',
    },
    A_QUESTION_REFUND: {
        'permission': 'user.is_staff or user.game_editor or user.is_superuser',
        'function': 'refund_question(data.get("question_id"))',
    },
    A_MAKE_GAME_EDITOR: {
        'permission': 'user.is_superuser',
        'function': 'make_game_editor(data.get("user_id"))',
    },
    A_REMOVE_GAME_EDITOR: {
        'permission': 'user.is_superuser',
        'function': 'remove_game_editor(data.get("user_id"))',
    },
    A_REFUND_BET: {
        'permission': 'user.is_superuser',
        'function': 'refund_bet(data.get("bet_id"), data.get("percent"))',
    },
    A_DEPOSIT_ACCEPT: {
        'permission': 'user.is_superuser',
        'function': 'accept_deposit(data.get("deposit_id"))',
    },
    A_DEPOSIT_CANCEL: {
        'permission': 'user.is_superuser',
        'function': 'cancel_deposit(data.get("deposit_id"))',
    },
    A_WITHDRAW_ACCEPT: {
        'permission': 'user.is_superuser',
        'function': 'accept_withdraw(data.get("withdraw_id"))',
    },
    A_WITHDRAW_CANCEL: {
        'permission': 'user.is_superuser',
        'function': 'cancel_withdraw(data.get("withdraw_id"))',
    },
    A_TRANSFER_ACCEPT: {
        'permission': 'user.is_superuser',
        'function': 'accept_transfer(data.get("transfer_id"))',
    },
    A_TRANSFER_CANCEL: {
        'permission': 'user.is_superuser',
        'function': 'cancel_transfer(data.get("transfer_id"))',
    },
}
