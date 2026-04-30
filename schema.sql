-- ============================================================
--  Crypto Portfolio & Leverage Tracker — FULL MySQL Schema
--  CS 2005: Database Systems — Spring 2026
--  9 Tables, 5 Views, 5 Stored Procedures, 2 Triggers
-- ============================================================

CREATE DATABASE IF NOT EXISTS crypto_tracker;
USE crypto_tracker;

-- ============================================================
-- TABLE 1: users
-- ============================================================
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin','trader') NOT NULL DEFAULT 'trader',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE 2: wallets
-- ============================================================
CREATE TABLE wallets (
    wallet_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    wallet_name VARCHAR(100) NOT NULL,
    wallet_type ENUM('spot','margin','futures') NOT NULL DEFAULT 'spot',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 3: assets  (current holdings per wallet)
-- ============================================================
CREATE TABLE assets (
    asset_id      INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id     INT           NOT NULL,
    symbol        VARCHAR(20)   NOT NULL,
    quantity      DECIMAL(20,8) NOT NULL DEFAULT 0,
    avg_buy_price DECIMAL(20,8) NOT NULL DEFAULT 0,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallets(wallet_id) ON DELETE CASCADE,
    UNIQUE KEY uq_wallet_symbol (wallet_id, symbol)
);

-- ============================================================
-- TABLE 4: trades
-- ============================================================
CREATE TABLE trades (
    trade_id   INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id  INT           NOT NULL,
    symbol     VARCHAR(20)   NOT NULL,
    trade_type ENUM('buy','sell') NOT NULL,
    quantity   DECIMAL(20,8) NOT NULL,
    price      DECIMAL(20,8) NOT NULL,
    fee        DECIMAL(20,8) NOT NULL DEFAULT 0,
    trade_date DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes      TEXT,
    FOREIGN KEY (wallet_id) REFERENCES wallets(wallet_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 5: leverage_positions
-- ============================================================
CREATE TABLE leverage_positions (
    position_id       INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id         INT           NOT NULL,
    symbol            VARCHAR(20)   NOT NULL,
    direction         ENUM('long','short') NOT NULL,
    leverage          DECIMAL(5,2)  NOT NULL,
    entry_price       DECIMAL(20,8) NOT NULL,
    quantity          DECIMAL(20,8) NOT NULL,
    margin_used       DECIMAL(20,8) NOT NULL,
    liquidation_price DECIMAL(20,8),
    status            ENUM('open','closed') NOT NULL DEFAULT 'open',
    opened_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at         DATETIME,
    close_price       DECIMAL(20,8),
    realized_pnl      DECIMAL(20,8),
    FOREIGN KEY (wallet_id) REFERENCES wallets(wallet_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 6: price_cache  (CoinGecko API snapshots)
-- ============================================================
CREATE TABLE price_cache (
    cache_id   INT AUTO_INCREMENT PRIMARY KEY,
    symbol     VARCHAR(20)   NOT NULL,
    price_usd  DECIMAL(20,8) NOT NULL,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_fetched (symbol, fetched_at)
);

-- ============================================================
-- TABLE 7: notifications
-- ============================================================
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT          NOT NULL,
    type            ENUM('price_alert','trade_confirm','liquidation_warning','system') NOT NULL,
    message         TEXT         NOT NULL,
    is_read         TINYINT(1)   NOT NULL DEFAULT 0,
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 8: audit_log  (tracks every significant action)
-- ============================================================
CREATE TABLE audit_log (
    log_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT          NOT NULL,
    action     VARCHAR(50)  NOT NULL,
    table_name VARCHAR(50)  NOT NULL,
    record_id  INT,
    old_value  TEXT,
    new_value  TEXT,
    logged_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 9: portfolio_snapshots  (daily portfolio value history)
-- ============================================================
CREATE TABLE portfolio_snapshots (
    snapshot_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    snapshot_date DATE          NOT NULL,
    total_value   DECIMAL(20,8) NOT NULL DEFAULT 0,
    total_cost    DECIMAL(20,8) NOT NULL DEFAULT 0,
    total_pnl     DECIMAL(20,8) NOT NULL DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_date (user_id, snapshot_date),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);


-- ============================================================
-- VIEWS
-- ============================================================

-- VIEW 1: Full trade details (JOIN: trades + wallets + users)
CREATE OR REPLACE VIEW vw_trade_details AS
SELECT
    t.trade_id,
    u.username,
    u.email,
    w.wallet_name,
    w.wallet_type,
    t.symbol,
    t.trade_type,
    t.quantity,
    t.price,
    t.fee,
    ROUND(t.quantity * t.price, 2)         AS gross_value,
    ROUND(t.quantity * t.price + t.fee, 2) AS net_value,
    t.trade_date
FROM trades  t
JOIN wallets w ON t.wallet_id = w.wallet_id
JOIN users   u ON w.user_id   = u.user_id;

-- VIEW 2: Portfolio holdings with full context
CREATE OR REPLACE VIEW vw_portfolio_holdings AS
SELECT
    u.user_id,
    u.username,
    w.wallet_id,
    w.wallet_name,
    w.wallet_type,
    a.symbol,
    a.quantity,
    a.avg_buy_price,
    ROUND(a.quantity * a.avg_buy_price, 2) AS cost_basis
FROM assets  a
JOIN wallets w ON a.wallet_id = w.wallet_id
JOIN users   u ON w.user_id   = u.user_id;

-- VIEW 3: All open leverage positions with user context
CREATE OR REPLACE VIEW vw_open_positions AS
SELECT
    u.username,
    w.wallet_name,
    lp.position_id,
    lp.symbol,
    lp.direction,
    lp.leverage,
    lp.entry_price,
    lp.quantity,
    lp.margin_used,
    lp.liquidation_price,
    lp.opened_at
FROM leverage_positions lp
JOIN wallets w ON lp.wallet_id = w.wallet_id
JOIN users   u ON w.user_id    = u.user_id
WHERE lp.status = 'open';

-- VIEW 4: Per-user trade statistics (aggregate + built-in functions)
CREATE OR REPLACE VIEW vw_user_trade_stats AS
SELECT
    u.user_id,
    u.username,
    COUNT(t.trade_id)                          AS total_trades,
    SUM(CASE WHEN t.trade_type='buy'  THEN 1 ELSE 0 END) AS buy_count,
    SUM(CASE WHEN t.trade_type='sell' THEN 1 ELSE 0 END) AS sell_count,
    ROUND(SUM(t.quantity * t.price), 2)        AS total_volume_usd,
    ROUND(AVG(t.quantity * t.price), 2)        AS avg_trade_size,
    ROUND(SUM(t.fee), 2)                       AS total_fees_paid,
    MIN(t.trade_date)                          AS first_trade,
    MAX(t.trade_date)                          AS last_trade
FROM users u
LEFT JOIN wallets w ON u.user_id   = w.user_id
LEFT JOIN trades  t ON w.wallet_id = t.wallet_id
GROUP BY u.user_id, u.username;

-- VIEW 5: Platform-wide admin summary (subqueries + aggregate)
CREATE OR REPLACE VIEW vw_platform_stats AS
SELECT
    (SELECT COUNT(*) FROM users)                                           AS total_users,
    (SELECT COUNT(*) FROM wallets)                                         AS total_wallets,
    (SELECT COUNT(*) FROM trades)                                          AS total_trades,
    (SELECT COUNT(*) FROM leverage_positions WHERE status='open')          AS open_positions,
    (SELECT COUNT(*) FROM leverage_positions WHERE status='closed')        AS closed_positions,
    (SELECT ROUND(SUM(quantity * price), 2) FROM trades)                   AS total_platform_volume,
    (SELECT ROUND(SUM(realized_pnl), 2)
     FROM leverage_positions WHERE status='closed')                        AS total_realized_pnl;


-- ============================================================
-- STORED PROCEDURES
-- ============================================================

DELIMITER $$

-- PROCEDURE 1 (Trader): Record a trade + update asset (with TRANSACTION)
CREATE PROCEDURE sp_record_trade(
    IN p_wallet_id INT,
    IN p_symbol    VARCHAR(20),
    IN p_type      ENUM('buy','sell'),
    IN p_qty       DECIMAL(20,8),
    IN p_price     DECIMAL(20,8),
    IN p_fee       DECIMAL(20,8),
    IN p_notes     TEXT
)
BEGIN
    DECLARE v_existing_qty DECIMAL(20,8) DEFAULT 0;
    DECLARE v_existing_avg DECIMAL(20,8) DEFAULT 0;
    DECLARE v_new_avg      DECIMAL(20,8);
    DECLARE v_new_qty      DECIMAL(20,8);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    INSERT INTO trades (wallet_id, symbol, trade_type, quantity, price, fee, notes)
    VALUES (p_wallet_id, UPPER(p_symbol), p_type, p_qty, p_price, p_fee, p_notes);

    IF p_type = 'buy' THEN
        SELECT COALESCE(quantity,0), COALESCE(avg_buy_price,0)
        INTO v_existing_qty, v_existing_avg
        FROM assets
        WHERE wallet_id = p_wallet_id AND symbol = UPPER(p_symbol)
        LIMIT 1;

        SET v_new_qty = v_existing_qty + p_qty;
        SET v_new_avg = (v_existing_avg * v_existing_qty + p_price * p_qty) / v_new_qty;

        INSERT INTO assets (wallet_id, symbol, quantity, avg_buy_price)
        VALUES (p_wallet_id, UPPER(p_symbol), v_new_qty, v_new_avg)
        ON DUPLICATE KEY UPDATE
            quantity      = v_new_qty,
            avg_buy_price = v_new_avg;

    ELSE
        SELECT COALESCE(quantity,0) INTO v_existing_qty
        FROM assets
        WHERE wallet_id = p_wallet_id AND symbol = UPPER(p_symbol) LIMIT 1;

        IF v_existing_qty IS NULL OR v_existing_qty < p_qty THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Insufficient balance for sell';
        END IF;

        SET v_new_qty = v_existing_qty - p_qty;
        IF v_new_qty = 0 THEN
            DELETE FROM assets WHERE wallet_id = p_wallet_id AND symbol = UPPER(p_symbol);
        ELSE
            UPDATE assets SET quantity = v_new_qty
            WHERE wallet_id = p_wallet_id AND symbol = UPPER(p_symbol);
        END IF;
    END IF;

    COMMIT;
END$$


-- PROCEDURE 2 (Trader): Open a leverage position (with TRANSACTION)
CREATE PROCEDURE sp_open_position(
    IN p_wallet_id   INT,
    IN p_symbol      VARCHAR(20),
    IN p_direction   ENUM('long','short'),
    IN p_leverage    DECIMAL(5,2),
    IN p_entry_price DECIMAL(20,8),
    IN p_quantity    DECIMAL(20,8),
    IN p_margin      DECIMAL(20,8)
)
BEGIN
    DECLARE v_liq DECIMAL(20,8);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; RESIGNAL; END;

    IF p_direction = 'long' THEN
        SET v_liq = p_entry_price * (1 - 1/p_leverage);
    ELSE
        SET v_liq = p_entry_price * (1 + 1/p_leverage);
    END IF;

    START TRANSACTION;
    INSERT INTO leverage_positions
        (wallet_id, symbol, direction, leverage, entry_price,
         quantity, margin_used, liquidation_price, status)
    VALUES
        (p_wallet_id, UPPER(p_symbol), p_direction, p_leverage,
         p_entry_price, p_quantity, p_margin, v_liq, 'open');
    COMMIT;
END$$


-- PROCEDURE 3 (Trader): Close a leverage position and record PnL
CREATE PROCEDURE sp_close_position(
    IN p_position_id INT,
    IN p_close_price DECIMAL(20,8)
)
BEGIN
    DECLARE v_dir     VARCHAR(10);
    DECLARE v_entry   DECIMAL(20,8);
    DECLARE v_qty     DECIMAL(20,8);
    DECLARE v_lev     DECIMAL(5,2);
    DECLARE v_pnl     DECIMAL(20,8);
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN ROLLBACK; RESIGNAL; END;

    START TRANSACTION;

    SELECT direction, entry_price, quantity, leverage
    INTO v_dir, v_entry, v_qty, v_lev
    FROM leverage_positions
    WHERE position_id = p_position_id AND status = 'open'
    FOR UPDATE;

    IF v_dir IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Position not found or already closed';
    END IF;

    SET v_pnl = IF(v_dir='long',
        (p_close_price - v_entry) * v_qty * v_lev,
        (v_entry - p_close_price) * v_qty * v_lev);

    UPDATE leverage_positions
    SET status='closed', close_price=p_close_price,
        closed_at=NOW(), realized_pnl=v_pnl
    WHERE position_id = p_position_id;

    COMMIT;
END$$


-- PROCEDURE 4 (Admin): Full report for a user
CREATE PROCEDURE sp_user_portfolio_report(IN p_user_id INT)
BEGIN
    SELECT a.symbol, a.quantity, a.avg_buy_price,
           ROUND(a.quantity * a.avg_buy_price,2) AS cost_basis,
           w.wallet_name, w.wallet_type
    FROM assets a JOIN wallets w ON a.wallet_id = w.wallet_id
    WHERE w.user_id = p_user_id ORDER BY cost_basis DESC;

    SELECT symbol, trade_type,
           COUNT(*)                        AS trades,
           ROUND(SUM(quantity*price),2)    AS total_volume
    FROM trades
    WHERE wallet_id IN (SELECT wallet_id FROM wallets WHERE user_id=p_user_id)
    GROUP BY symbol, trade_type ORDER BY total_volume DESC;
END$$


-- PROCEDURE 5 (Admin): Clean up stale price cache
CREATE PROCEDURE sp_cleanup_price_cache(IN p_hours INT)
BEGIN
    DELETE FROM price_cache
    WHERE fetched_at < DATE_SUB(NOW(), INTERVAL p_hours HOUR);
    SELECT ROW_COUNT() AS rows_deleted;
END$$


DELIMITER ;


-- ============================================================
-- TRIGGERS
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_audit_trade_insert
AFTER INSERT ON trades FOR EACH ROW
BEGIN
    DECLARE v_uid INT;
    SELECT user_id INTO v_uid FROM wallets WHERE wallet_id=NEW.wallet_id LIMIT 1;
    INSERT INTO audit_log (user_id, action, table_name, record_id, new_value)
    VALUES (v_uid, 'INSERT_TRADE', 'trades', NEW.trade_id,
            CONCAT(NEW.trade_type,' ',NEW.quantity,' ',NEW.symbol,' @ $',NEW.price));
END$$

CREATE TRIGGER trg_audit_position_close
AFTER UPDATE ON leverage_positions FOR EACH ROW
BEGIN
    DECLARE v_uid INT;
    IF NEW.status='closed' AND OLD.status='open' THEN
        SELECT user_id INTO v_uid FROM wallets WHERE wallet_id=NEW.wallet_id LIMIT 1;
        INSERT INTO audit_log (user_id, action, table_name, record_id, old_value, new_value)
        VALUES (v_uid, 'CLOSE_POSITION', 'leverage_positions', NEW.position_id,
                CONCAT('OPEN @ ',OLD.entry_price),
                CONCAT('CLOSED @ ',NEW.close_price,' PnL: ',NEW.realized_pnl));
    END IF;
END$$

DELIMITER ;


-- ============================================================
-- SEED DATA
-- ============================================================
INSERT INTO users (username, email, password_hash, role) VALUES
  ('admin',   'admin@cryptotracker.com',   '$2b$12$admin_hash',   'admin'),
  ('trader1', 'trader1@cryptotracker.com', '$2b$12$trader1_hash', 'trader'),
  ('trader2', 'trader2@cryptotracker.com', '$2b$12$trader2_hash', 'trader');

INSERT INTO wallets (user_id, wallet_name, wallet_type) VALUES
  (2, 'Main Spot Wallet', 'spot'),
  (2, 'Futures Account',  'futures'),
  (3, 'Spot Holdings',    'spot');

INSERT INTO assets (wallet_id, symbol, quantity, avg_buy_price) VALUES
  (1,'BTC', 0.50,  60000.00),
  (1,'ETH', 4.00,   3000.00),
  (1,'SOL',20.00,    150.00),
  (3,'BTC', 0.25,  58000.00),
  (3,'ADA',500.0,     0.45);

INSERT INTO trades (wallet_id, symbol, trade_type, quantity, price, fee) VALUES
  (1,'BTC','buy', 0.50,  60000, 15.00),
  (1,'ETH','buy', 4.00,   3000,  6.00),
  (1,'SOL','buy',20.00,    150,  1.50),
  (3,'BTC','buy', 0.25,  58000, 14.50),
  (3,'ADA','buy',500.0,   0.45,  0.50);

INSERT INTO leverage_positions
  (wallet_id,symbol,direction,leverage,entry_price,quantity,margin_used,liquidation_price,status) VALUES
  (2,'BTC','long', 10.00,62000.00,0.1,620.00,55800.00,'open'),
  (2,'ETH','short', 5.00, 3200.00,1.0,640.00, 3840.00,'open');

INSERT INTO notifications (user_id,type,message) VALUES
  (2,'trade_confirm',      'BTC buy order of 0.5 BTC at $60,000 confirmed.'),
  (2,'liquidation_warning','BTC long approaching liquidation at $55,800.');
