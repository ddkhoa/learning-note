## Introduction
When it comes to query performance, indexes are commonly referred to as the magic remediation. In most cases, indexes speed up queries significantly. But why?
In this article, we will look at the Index Scan operation in Postgres.
- Explain why the index is fast in certain situations
- The scenario in which indexing is not a good choice
- Additional operation to improve index scan

The article only examine BTREE indexes.

## Sequential Scan & Index Scan
To understand why index scan is fast, we use Sequential Scan operation as the baseline. Sequential Scan operation is the default option of Postgres if no indexes are available.

### First insight
First, we examine the procedure of Sequential Scan and Index Scan operation.

- In a sequential Scan operation, PG visits the heap space. It reads all the table data, page by page. Then it checks every tuple if it matches the filter condition and is visible for the query.
- In an Index Scan operation, PG does the following actions, in order:
  - PG visits the index space first and finds the relevant index tuples.
  - Index tuples are pointers to heap tuples. It contains information to locate the tuple in the heap space: the page and offset. PG uses this information to read the page and retrieve the relevant tuples.

By comparing these two procedures, we can gain the first insight into index scan performance. PG identifies the data it need using index. Then it only visits a few blocks instead of the whole table.

However, this is a qualitative statement. What if the number of blocks identified by index is important?

We need a quantitative analysis. PG has a sophisticated system to evaluate the cost of an execution plan. Higher costs lead to slower the operations. We will compare the cost of sequential scan and index scan.

### Quantitative analysis

#### Postgres cost constants
In PG, the term of `cost` refers to a number in an arbitrary unit, that indicates how heavy the operation is. The following are the costs of basic operations in PG:

**seq_page_cost**: Cost to fetch a page from disk in a series. Default value is 1.0.

**random_page_cost**: Cost to fetch a page from disk randomly. Default value is 4.0.

**cpu_tuple_cost**: Cost to process a data entry. Default value is 0.01.

**cpu_index_tuple_cost**: Cost to process an index entry. Default value is 0.005.

**cpu_operator_cost**: Cost of execute an operator in a query. Default value is 0.0025.

#### Sequential Scan cost
Sequential scan cost consists of CPU cost and IO cost
$$sequential\\_scan\\_cost = seq\\_cpu\\_cost + seq\\_IO\\_cost$$

In a sequential scan, PG must visit all the pages and check all the tuples against the conditions.
$$seq\\_cpu\\_cost = (cpu\\_tuple\\_cost + nb\\_operators\\_in\\_query * cpu\\_operator\\_cost) * n\\_tuples$$

Heap pages read are sequential.
$$seq\\_IO\\_cost = seq\\_page\\_cost * n\\_pages$$

$$sequential\\_scan\\_cost = (0.01 + nb\\_operators\\_in\\_query * 0.0025) * n\\_tuples + n\\_pages$$

Given a query on a table, `nb_operators_in_query`, `n_pages` and `n_tuples` are constants, so `sequential_scan_cost` is also a constant. It doesn't depend on the number of rows we want to retrieve.

#### Index Scan cost
In an index scan, there are 2 steps: visit the index space and the heap space:
$$index\\_scan\\_cost = index\\_cost + table\\_cost$$

Each stage has it own cpu cost and IO cost:
$$index\\_cost = index\\_cpu\\_cost + index\\_IO\\_cost$$
$$table\\_cost = table\\_cpu\\_cost + table\\_IO\\_cost$$

Index CPU cost consists of the cost to traverse the tree to find relevant index tuples and the cost to process those tuples[1]:
$$index\\_cpu\\_cost = tree\\_traversal\\_cost + (cpu\\_index\\_tuple\\_cost + cpu\\_operator\\_cost) * n\\_index\\_tuples\\_read$$ 

[@TODO]
$$tree\\_traversal\\_cost = ceil(log(n\\_index\\_tuples)/log(2)) * cpu\\_operator\\_cost + 50 * cpu\\_operator\\_cost * (tree\\_height + 1)$$ 

[@TODO]
$$n\\_index\\_tuples\\_read = S * n\\_index\\_tuples$$ 


$$index\\_cpu\\_cost = ceil(log(n\\_index\\_tuples)/log(2)) * 0.0025 + 0.125 * tree\\_height + 0.125 + 0.0075 * S * n\\_index\\_tuples$$


Index pages are read randomly 
$$index\\_IO\\_cost = random\\_page\\_cost * n\\_index\\_pages\\_fetched$$

Same as above
$$n\\_index\\_pages\\_fetched = S * n\\_index\\_pages$$

$$index\\_IO\\_cost = 4 * S * n\\_index\\_pages$$


$$index\\_cost = ceil(log(n\\_index\\_tuples)/log(2)) * 0.0025 + 0.125 * tree\\_height + 0.125 + 0.0075 * S * n\\_index\\_tuples + 4 *  S * n\\_index\\_pages$$

In case of n_index_tuples is large:
- `log(n_index_tuples) << n_index_tuples`.
- `tree_height ~ log(n_index_tuples) (?) << n_index_tuples`
- `n_index_pages = k * n_index_tuples` (k < 1). We keep n_index_pages in the equation.

The index cost formula can be simplified as: 
$$index\\_cost = 0.0075 * S * n\\_index\\_tuples + 4 * S * n\\_index\\_pages$$


$$table\\_cpu\\_cost =  (cpu\\_tuple\\_cost + cpu\\_operator\\_cost) * n\\_tuples\\_fetched$$

$$n\\_tuples\\_fetched = S * n\\_tuples$$
$$table\\_cpu\\_cost = 0.0125 * S * n\\_tuples$$

To estimate table_IO_cost, we consider a new notion: Index Correlation. It indicates the similarity between the logical order of index entries and the physical order of corresponds heap entries. The range of index correlation values is [-1, 1]. The value 1 means index entries and heap entries are in the same order. The value -1 means they are in inverted order. When this value is 0, there are no correlation at all between them.

**Best case**

In case of high correlation, the order of index entries and heap entries totally match. Then the first heap visit is random, but all subsequent reads are sequential. In addition, the number of heap pages to read is the fraction of the table identified by index_selectivity.

$$table\\_IO\\_cost\\_best\\_case = random\\_page\\_cost + seq\\_page\\_cost * (S * n\\_pages - 1)$$
$$table\\_IO\\_cost\\_best\\_case = 3  + S * n\\_pages$$

**Worst case**

In case of low correlation, PG use an approximation of number page to fetch

```C++
 * We use an approximation proposed by Mackert and Lohman, "Index Scans
 * Using a Finite LRU Buffer: A Validated I/O Model", ACM Transactions
 * on Database Systems, Vol. 14, No. 3, September 1989, Pages 401-424.
 * The Mackert and Lohman approximation is that the number of pages
 * fetched is
 *	PF =
    *		min(2TNs/(2T+Ns), T)			when T <= b
    *		2TNs/(2T+Ns)					when T > b and Ns <= 2Tb/(2T-b)
    *		b + (Ns - 2Tb/(2T-b))*(T-b)/T	when T > b and Ns > 2Tb/(2T-b)
```

We play with the function to understand how PF depends on each parameter.

**Fixed T, N, and b. Find the relation between PF and s**
- When T <= b, PF increase quickly, then it is bounded by T.
- When T > b, PF still increase quickly, then when s exceeds the threshold 2Tb/N*(2T-b), PF increase linearly regards to s.

In both cases, PF is very sensitive to s.

**Fixed T, N and s. Find the relation between PF and b**
- Of course, when the cache size increase, the number of PF decrease. If PG found a page in cache, the no page fetched from disk is needed.

**Fixed b and s. Find the relation between PF and T**

In this scenario, we replace N by k * T
- For small s (0.01), PF increase linearly to T.
- When we use a higher value of s (0.1), we notice a "break" in the graph. When table size exceeds cache size, the velocity of PF increase more quickly than before.

We interested in the relation between PF and s. Then the IO cost in the worst case is compute like following:
$$table\\_IO\\_cost\\_worst\\_case = 4 * PF$$


## Cluster

## Conclusion
Pattern: Search many elements by index on a large table

[1] Postgres source code: `/src/backend/utils/adt/selfuncs.c`, function `btcostestimate`