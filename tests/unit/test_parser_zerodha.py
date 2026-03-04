from tt_connect.brokers.zerodha.parser import parse

def test_parse_counts(zerodha_csv):
    result = parse(zerodha_csv)
    assert len(result.indices)  == 2
    assert len(result.equities) == 3
    assert len(result.futures)  == 3
    assert len(result.options)  == 4

def test_index_canonical_name(zerodha_csv):
    result = parse(zerodha_csv)
    nifty = next(i for i in result.indices if i.symbol == "NIFTY")
    assert nifty.exchange == "NSE"
    assert nifty.broker_symbol == "NIFTY 50"

def test_future_underlying_exchange(zerodha_csv):
    result = parse(zerodha_csv)
    # NFO future should have underlying_exchange NSE
    nfo_fut = next(f for f in result.futures if f.exchange == "NFO")
    assert nfo_fut.underlying_exchange == "NSE"
    
    # BFO future should have underlying_exchange BSE
    bfo_fut = next(f for f in result.futures if f.exchange == "BFO")
    assert bfo_fut.underlying_exchange == "BSE"

def test_option_strike_is_float(zerodha_csv):
    result = parse(zerodha_csv)
    for opt in result.options:
        assert isinstance(opt.strike, float)

def test_option_type_values(zerodha_csv):
    result = parse(zerodha_csv)
    types = {o.option_type for o in result.options}
    assert types == {"CE", "PE"}

def test_unknown_exchange_skipped():
    # Adding an MCX row to the CSV content
    mcx_row = "1000008,40008,GOLD26FEBFUT,GOLD,0,2026-02-26,0,0.01,1,FUT,MCX-FUT,MCX"
    csv_content = (
        "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n"
        + mcx_row
    )
    result = parse(csv_content)
    assert len(result.indices) == 0
    assert len(result.equities) == 0
    assert len(result.futures) == 0
    assert len(result.options) == 0
