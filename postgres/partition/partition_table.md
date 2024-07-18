## Partition table in PostgreSQL
### Context
In the database, there is usually one or some tables that are gigantic and scale quickly compared to others. For example, in a supermarket chain system, the table `product` can have about 100K lines and is quite static. Conversely, the table `transaction` table can have up to billions of lines and scale indefinitely. For a chat application, the table `messages` outweighs other tables in the same way.

These big tables are also the most critical ones in the database. Most DML queries are made against them. Therefore, configuring and optimizing those tables properly greatly impacts the whole system. Partitioning is a technique to deal with large tables.

### Definition
Partitioning is the act of dividing a *big* table into many smaller parts (partitions). There is a *parent* table that is the entry point to query data. However, data is not stored in the parent table but in each partition. Partitioning changes how data is organized on disk but does not introduce modifications in the application code.

### Impact
Partitioning, when done properly, can improve some aspects of the databases. However, this tool also comes with some limitations.

#### Query performance
PostgreSQL implements different techniques to optimize a query on a partitioned table. They are `partition pruning`, `partitionwise join`, and `partitionwise aggregate`.

**Partition pruning**
With partition pruning, the engine examines the table structures to determine the partition(s) that are useful for the query and discard others. Therefore, the search space is reduced.

We should be clear about the performance difference between a non-partitioned and a partitioned table in case of searching by a *selective* index. In this case, the number of rows to retrieve is small. `Index Scan` strategy is employed in which the engine visits the index space first to retrieve index tuples. Then the engine does some heap fetches to get the data. The time to find the index tuples is O(logN). Even with `partition pruning`, the difference in response time between a non-partitioned and a partitioned table is opaque in this situation.

`Partition pruning`'s effect becomes visible when the query targets more rows. Searching by index on a big table can be *slower* than a sequential scan on a partition because the cost of fetching many index pages and heap pages in a **non-sequential** order outweighs the cost of sequential fetches plus checking the condition on a smaller data set. 

> Partitioning can improve query performance by turning an index scan on a big table into a sequential scan on a partition, using the partition pruning technique.

**Partitionwise join and partitionwise aggregate**
When joining 2 partitioned tables, `partitionwise join` allows the join to be done on each matching partition rather than the whole table. In my work, I haven't used this option yet. 

When the `GROUP BY` clause doesn't contain any columns used to partition the table, then `partitionwise aggregate` could help. It allows the group by (and all precedent operations) to be done on each partition separately. Based on the hardware configuration, the engine can execute some operations in parallel and accelerate the execution. In my experience, it's not easy to achieve a big gain using `partitionwise aggregate` due to the following challenges:

- If a partition is significantly larger than others, the impact of parallelism is canceled.
- The number of workers is smaller than the number of parallel-able tasks.

**Warning**
Make sure queries made on a partition table always include the partition columns. Otherwise, the engine will generate a complex execution plan that **spans all partitions**.

As a rule of thumb, always **benchmark** different partition columns to choose the best one.

#### Table unique constraints and indexes
Partitioning has some drawbacks that a non-partition table doesn't have. In a partitioned table, each partition is a complete and independent entity. This creates limits and extra work when we want to create a unique constraint or an index across partitions.

**Unique constraints**
The engine only guarantees intra-partition uniqueness. As a consequence, global unique constraints must include all partition columns.

**Indexes**
`CREATE INDEX CONCURRENTLY` query cannot be run on a partitioned table. However, we can still create such an index while avoiding locking the table. The process is:

- Create the index on the parent table using the `ON ONLY` option
- Create the index on each partition using the `CONCURRENTLY` option
- Attach each partition index to the parent index

#### Maintenance operations
Partitioning a big table makes maintenance operations like `ANALYZE` and `VACUUM` run more frequently and smoother.

`ANALYZE` query collects data statistics which are used by the engine to determine the most efficient execution plan. The amount of data collected is *proportioned* to the number of rows in a table. For a big table, the `ANALYZE` query can be very long. In the windows when this command has not been finished, the statistics are not available and queries made against the table could be resource-intensive and time-consuming.

The `VACUUM` query removes obsolete rows of a table. During the vacuum process, the space previously occupied by obsolete rows is cleaned up and can be reused by the same table. VACUUM regularly is necessary to prevent dead data from accumulating and slowing down queries. The VACUUM is automatically triggered when inserted or updated and deleted rows exceed a threshold *relative* to the table's size (configured by `autovacuum_vacuum_insert_scale_factor` and `autovacuum_vacuum_scale_factor`). Like the `ANALYZE` query, `VACUUM` a big table is a time-consuming task. Worse, because there is a lot of data to vacuum on a big table, the cost of this operation can exceed the limit (`autovacuum_vacuum_cost_limit`), and the vacuum is slowed down ( `autovacuum_vacuum_cost_delay`). In this situation, the table usually ends up being bloated.

When the table is divided into partitions, each partition can be vacuumed and analyzed separately. Because the partition is way smaller than the original table, the `VACUUM` and `ANALYZE` operations for a partition can finish faster. Multiple `VACUUM ANALYZE` commands can be run in parallel (configured by `autovacuum_max_workers`) to accelerate the process.

I had bad memories of the `VACUUM ANALYZE` query. One night, I upgraded the server to the new major version. Because the statistics were not transferred, I analyzed all the tables and the process took too long. Queries run on the big table consumed all available CPU and slowed down the server. I wasn't aware of the issue until checking the system the following day. Accelerating the `VACUUM ANALYZE` query was the main reason for partitioning that table.

### Partition methods in PostgreSQL
PostgreSQL has 3 inherent modes to partition a table: **Range Partitioning**, **List Partitioning**, and **Hash Partitioning**

#### Range Partitioning
In this mode, we determine some `ranges` to group data into partitions. The method is suitable for partitioning data using continuous value columns. In practice, when we are interested in recent data more than historical ones, then the `date` column is a natural candidate to partition the table using `range partitioning`. With `partition pruning`, the query that gets last year's data works on a relatively fixed amount of data thus providing a consistent response time, regardless of how old the system is.

#### List Partitioning
In this mode, we specify a list of values for each partition. This method can be employed when partition columns contain discrete values. One constraint is that we should know the list of possible values beforehand. An error will be thrown during data ingestion if the engine receives an unknown value and cannot find the right partition. 

#### Hash Partitioning
The two previous methods might need some business context to determine the appropriate scope of each partition. In contrast, hash partitioning is a purely technical approach to dividing the table into groups. This method can work with a surrogate key. Suppose we want to create N partitions for the table. The engine will compute, for each key, a value V between 0 and N - 1 and put the record to the partition V. If you don't use the default function provided by PostgreSQL, the hash function should be *wisely* chosen so that data is divided equally between partitions.

### Conclusion
In this article, we discussed about `partitioning` in PostgreSQL. We point out its advantages and limitations. We saw that partitioning a table improves the query performance in some *specific* cases, but not all the time. This tool also comes with some limitations that we should be aware of before modifying the production database. `VACUUM` and `ANALYZE` processes will run smoother on partitioned tables. Finally, we talked about different partitioning methods in PostgreSQL.