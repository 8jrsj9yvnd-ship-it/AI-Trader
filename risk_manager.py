import config


def calculate_position_size(account_value, entry_price, atr=None):
    """
    Cortex Risk Manager

    Calculates:
    - Dollar risk allowed
    - Stop loss
    - Take profit
    - Share size
    - Position value

    If atr is provided, the stop distance is volatility-adjusted
    (ATR_STOP_MULTIPLIER * atr) instead of a flat STOP_LOSS_PERCENT.
    """


    if account_value <= 0:
        raise ValueError("Account value must be greater than zero")


    if entry_price <= 0:
        raise ValueError("Entry price must be greater than zero")



    # Maximum money Cortex can lose on this trade
    risk_amount = account_value * config.RISK_PER_TRADE



    # Stop loss calculation
    if atr and atr > 0:
        stop_loss = round(
            entry_price - (config.ATR_STOP_MULTIPLIER * atr),
            2
        )
    else:
        stop_loss = round(
            entry_price * (1 - config.STOP_LOSS_PERCENT),
            2
        )


    risk_per_share = round(
        entry_price - stop_loss,
        2
    )


    if risk_per_share <= 0:
        raise ValueError(
            "Invalid stop loss calculation"
        )



    # Calculate shares based on risk
    shares = int(
        risk_amount / risk_per_share
    )



    # Maximum position size protection
    max_position_value = account_value * 0.10


    max_shares_by_value = int(
        max_position_value / entry_price
    )


    shares = min(
        shares,
        max_shares_by_value
    )



    if shares < 1:

        return {
            "approved": False,
            "reason": "Position size too small",
            "shares": 0
        }



    # Reward target
    take_profit = round(
        entry_price +
        (risk_per_share * config.TAKE_PROFIT_RATIO),
        2
    )



    position_value = round(
        shares * entry_price,
        2
    )



    return {

        "approved": True,

        "shares": shares,

        "entry": entry_price,

        "stop_loss": stop_loss,

        "take_profit": take_profit,

        "risk_amount": round(
            risk_amount,
            2
        ),

        "risk_per_share": risk_per_share,

        "position_value": position_value
    }



def calculate_trade(account_value, entry_price):
    """
    Compatibility wrapper for Cortex trade execution.
    """

    return calculate_position_size(
        account_value,
        entry_price
    )