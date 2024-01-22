# Using Change Data Capture to reduce index bloat
## Statement
We have a table called `Order` containing about 11 millions rows. Each row represents an order with the following fields:
- `market_id`: The id of market where the order is placed
- `order_id`: The order id
- `date`: The date when the order is placed
- `total_price`: The total price of order
- `number_items`: The number of items in the order

Data is sent to us as CSV files. Each file contains orders for 1 market in a month. Each file contains about 90 000 rows (3000 orders/day).

To update data, we delete rows by `market_id`, load the file into a temporary table before inserting them into the permanent table. This procedure, while being safe, creates a lot of dead tuples in both heap space and index spaces. The size of index increase permanently. In order to keep the table in good shape, we have to:
- Running VACUUM command periodically to reclaim disk space occupied by dead rows.
- Running REINDEX command periodically to save the index from bloating.
 
Keep in mind that, running these commands on a large table is a resource-consuming task. VACUUM command does not reduce the disk space so you might be charged more than what you actually use (aka money wasted!)

We want a efficient way to update data in `Order` table.

## Method
We can use change data capture (CDC) pattern to identify the different between data in the CSV file and those currently in the table `Order`. Instead of deleting all data of a market then reinserting them, we need to:
- Insert new orders
- Update existing orders that have been modified in the latest version
- Delete the orders that presented in the previous version but not in the latest version

### Define the notion of `difference`
In this example, we consider the total price or number items in the order can be modified, while `order_id`, `market_id` and date are static.

### Create the footprint
To know if an order has been modified between 2 load, we compute the footprint of the order. In the simplest form, footprint contains all the field that can be changed. By comparing the footprint of the same `order_id`, we know if it has been modified or not.

### Identify changes to made
Given 2 table: 
- compare_orders: the subset of the permanent table, containing current orders in the database for a month.
- tmp_orders: the temporary table containing data read from csv file.
 
We can identify new orders to update, changed order to modified and obsolete order to delete

#### New orders
These are rows in `tmp_orders` table where `id` does not exist in `compare_orders` table.

#### Updated orders
These are rows in `tmp_orders` table where `id` exist in `compare_orders` table but the footprint value in 2 tables are different.

We can handle new and updated orders in 1 single UPSERT command:
```sql
INSERT INTO orders 
SELECT tmp.market_id, tmp.order_id, tmp.date, tmp.total_price, tmp.nb_items FROM tmp_orders tmp 
LEFT JOIN compare_orders comp 
ON tmp.order_id = comp.order_id
WHERE comp.order_id IS NULL 
OR tmp.fingerprint != comp.fingerprint
ON CONFLICT (order_id) DO UPDATE
SET total_price = EXCLUDED.total_price, nb_items = EXCLUDED.nb_items;
```

#### Deleted orders
These are rows in `compare_orders` table where `id` does not exist in `tmp_orders` table.
```sql
    DELETE FROM orders WHERE order_id IN (
    SELECT comp.order_id order_id FROM compare_orders comp
    LEFT JOIN tmp_orders tmp
    ON comp.order_id = tmp.order_id
    WHERE tmp.order_id IS NULL
)
```
@TODO
## Experimentation
We benchmark 2 update methods in 3 scenarios:
- Low diff ratio
- Medium diff ratio
- High diff ratio

### Generate data
### Benchmark
### Result