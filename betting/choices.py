TYPE_DEPOSIT = 'deposit'
TYPE_WITHDRAW = 'withdraw'
METHOD_TRANSFER = 'transfer'
METHOD_BKASH = 'bkash'
METHOD_ROCKET = 'rocket'
METHOD_NAGAD = 'nagad'
METHOD_UPAY = 'upay'
METHOD_MCASH = 'mcash'
METHOD_MYCASH = 'mycash'
METHOD_SURECASH = 'surecash'
METHOD_TRUSTPAY = 'trustpay'
METHOD_CLUB = 'club'
SOURCE_REFER = 'refer'
SOURCE_COMMISSION = 'commission'
SOURCE_BANK = 'bank'

DEPOSIT_SOURCE = (
    (SOURCE_BANK, 'From Bank'),
    (SOURCE_REFER, 'Referral'),
    (SOURCE_COMMISSION, 'Club Commission'),
)

DEPOSIT_WITHDRAW_CHOICES = (
    (METHOD_BKASH, 'bKash'),
    (METHOD_ROCKET, 'DBBL Rocket'),
    (METHOD_NAGAD, 'Nagad'),
    (METHOD_UPAY, 'Upay'),
    (METHOD_MCASH, 'Mcash'),
    (METHOD_MYCASH, 'My Cash'),
    (METHOD_SURECASH, 'Sure Cash'),
    (METHOD_TRUSTPAY, 'Trust Axiata Pay'),
    (METHOD_TRANSFER, 'Transfer'),
    (METHOD_CLUB, 'Club W/D'),
    (SOURCE_COMMISSION, 'Commission'),
    (SOURCE_REFER, 'Referral'),
)

GAME_FOOTBALL = 'football'
GAME_CRICKET = 'cricket'
GAME_TENNIS = 'tennis'
GAME_OTHERS = 'others'
GAME_CHOICES = (
    (GAME_FOOTBALL, 'Football'),
    (GAME_CRICKET, 'Cricket'),
    (GAME_TENNIS, 'Tennis'),
    (GAME_OTHERS, 'Others')
)

COMMISSION_REFER = 'refer'
COMMISSION_CLUB = 'club'
COMMISSION_CHOICES = (
    (COMMISSION_REFER, 'Refer commission'),
    (COMMISSION_CLUB, 'Club commission'),
)
STATUS_LIVE = 'live'
STATUS_HIDDEN = 'hidden'
STATUS_CLOSED = 'closed'
STATUS_LOCKED = 'locked'
MATCH_STATUS_CHOICES = (
    (STATUS_LIVE, 'Live'),
    (STATUS_HIDDEN, 'Hidden'),
    (STATUS_CLOSED, 'Closed'),
    (STATUS_LOCKED, 'Locked'),
)
STATUS_PENDING = 'pending'
STATUS_PAID = 'paid'
STATUS_REFUNDED = 'refunded'
STATUS_CANCELLED = 'cancelled'
STATUS_AWAITING_RESULT = 'no result'
STATUS_CHOICES = (
    (STATUS_PENDING, 'Pending'),
    (STATUS_REFUNDED, 'Refunded'),
    (STATUS_PAID, 'Paid'),
    (STATUS_CANCELLED, 'Cancelled'),
    (STATUS_AWAITING_RESULT, 'No Result'),
)

A_MATCH_LOCK = 'lock_match'
A_MATCH_HIDE = 'hide_match'
A_MATCH_GO_LIVE = 'go_live_match'
A_MATCH_END_NOW = 'end_match_now'
A_QUESTION_LOCK = 'lock_question'
A_QUESTION_HIDE = 'hide_question'
A_QUESTION_END_NOW = 'end_now_question'
A_QUESTION_SELECT_WINNER = 'select_winner_question'
A_QUESTION_PAY = 'pay_question'
A_QUESTION_UN_PAY = 'un_pay_question'
A_QUESTION_REFUND = 'refund_question'
