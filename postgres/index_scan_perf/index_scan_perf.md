## Introduction
When it comes to query performance, indexes are usually referred to as the magic remediation. Indexes, in most cases, speed up queries a lot. But why?
In this article, we'll examine the Index Scan operation on Postgres.
- Explain why in most cases index is fast
- The scenario where index is not a good choice
- Additional operation to optimize index scan

## Sequential Scan & Index Scan
First, we examine the procedure of Sequential Scan and Index Scan operation.

### Sequential Scan operation
- PG visits the heap space. It reads all the table data, page by page. Then it checks every tuple if it matches the filter condition and is visible for the query.
  
### Index Scan operation
- PG visits the index space first and finds the relevant index tuples.
- Index tuples are pointers to heap tuples. It contains information to locate the tuple in the heap space: the page and offset. PG uses this information to read the page and retrieve the relevant tuples.

By comparing 2 procedures, we can have the first insight about index scan performance. By searching at first the relevant index tuples, PG does not need to visit all the available data.

However, that's a qualitative statement. We will quantify it. We know that PG has a sophisticated system to evaluate the cost of an execution plan. So we will use this.

The cost of an index scan depends on the number of index tuples that satisfy the condition. If there are a lot of rows, index scan must read many index pages and heap pages. Heap access in index scan is more expensive than in sequential scan, resulting in a higher cost.
In reality, we don't measure the index performance by the number of index tuples satisfying the condition but the ratio between that number and the number of rows in the table. We call that metric `selectivity`. Lower the `selectivity`, better the index.





## Correlation

## Cluster

## Conclusion
Pattern: Search many elements by index on a large table
