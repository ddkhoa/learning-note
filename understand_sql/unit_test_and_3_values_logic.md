# A story about unit testing and three-valued logic in SQL

## The setup

Imagine we have 2 tables, `metrics` and `metrics_values`, that store some metrics and their daily values.

```sql
CREATE TABLE metrics (
	id int,
	name varchar,
	parent_metric_id int
);

INSERT INTO metrics VALUES 
    (1, 'Metric A', 1),
    (2, 'Sub Metric A1', 1),
    (3, 'Metric B', 3), 
    (4, 'Sub Metric B1', 3);

CREATE TABLE metrics_values (
	id int,
	date date,
	value numeric
);

INSERT INTO metrics_values VALUES 
    (1, '2024-12-01', 100), 
    (1, '2024-12-02', 120), 
    (2, '2024-12-01', 50),
    (2, '2024-12-02', 55),
    (3, '2024-12-01', 40),
    (3, '2024-12-02', 38),
    (4, '2024-12-01', 20),
    (4, '2024-12-02', 25);
```

To retrieve the daily value and ratio of each metric, we can run the following query:

```sql
SELECT
	v1.id,
	v1.date,
	v1.value,
	v2.value,
	ROUND((v1.value / v2.value), 2) ratio
FROM
	metrics_values v1
	INNER JOIN metrics m ON v1.id = m.id
	INNER JOIN metrics_values v2 ON m.parent_metric_id = v2.id
		AND v1.date = v2.date
	ORDER BY
		v1.id,
		v1.date;
```

The result:

| id  |    date    | value | value | ratio |
| --- | ---------- | ----- | ----- | ----- |
| 1   | 2024-12-01 | 100   | 100   | 1.00  |
| 1   | 2024-12-02 | 120   | 120   | 1.00  |
| 2   | 2024-12-01 | 50    | 100   | 0.50  |
| 2   | 2024-12-02 | 55    | 120   | 0.46  |
| 3   | 2024-12-01 | 40    | 40    | 1.00  |
| 3   | 2024-12-02 | 38    | 38    | 1.00  |
| 4   | 2024-12-01 | 20    | 40    | 0.50  |
| 4   | 2024-12-02 | 25    | 38    | 0.66  |

So far, so good.

## What if a metric does not have any parent metric?

A metric might not have a parent metric. In that case, the value of `parent_metric_id` is NULL.

```sql
INSERT INTO metrics VALUES (5, 'Metric C', NULL);
INSERT INTO metrics_values VALUES (5, '2024-12-01', 30), (5, '2024-12-02', 30);
```

We need to include this metric in the result of the above query, with the ratio as NULL. Let's say we implemented a unit test that checks the value of metric 5 in the result before modifying the query.

We run the query. The test failed, of course. The rows related to the new metric are excluded from the result by the second join because `m.parent_metric_id` is NULL. 

We think about the following adjustment to the query:
1. Change the second join to LEFT JOIN to keep the value of metric 5 in the result.
2. Handle the case when v2.value is NULL, for example:

```sql
CASE WHEN v2.value IS NULL THEN NULL
ELSE 
    ROUND((v1.value / v2.value), 2)
END
```

We apply the first change to the query:

```sql
SELECT
	v1.id,
	v1.date,
	v1.value,
	v2.value,
	ROUND((v1.value / v2.value), 2) ratio
FROM
	metrics_values v1
	INNER JOIN metrics m ON v1.id = m.id
	LEFT JOIN metrics_values v2 ON m.parent_metric_id = v2.id
		AND v1.date = v2.date
	ORDER BY
		v1.id,
		v1.date;
```

The result:

| id  |    date    | value | value | ratio |
| --- | ---------- | ----- | ----- | ----- |
| 1   | 2024-12-01 | 100   | 100   | 1.00  |
| 1   | 2024-12-02 | 120   | 120   | 1.00  |
| 2   | 2024-12-01 | 50    | 100   | 0.50  |
| 2   | 2024-12-02 | 55    | 120   | 0.46  |
| 3   | 2024-12-01 | 40    | 40    | 1.00  |
| 3   | 2024-12-02 | 38    | 38    | 1.00  |
| 4   | 2024-12-01 | 20    | 40    | 0.50  |
| 4   | 2024-12-02 | 25    | 38    | 0.66  |
| 5   | 2024-12-01 | 30    | NULL  | NULL  |
| 5   | 2024-12-02 | 30    | NULL  | NULL  |

We have the metric 5 in the result. Its values are NULL. Great! But wait a second, we also have NULL in the column ratio, which mean the second step is not necessary!
But wait a second, the query ran without raising error, which mean we can **divide by NULL** in SQL?

And yes, we can!

## What did the SQL standard say about NULL?
For a long time, I thought that NULL represents missing values in SQL. As a consequence, arithmetic operators involving NULL would raise an error.

While the first part is true [1], the second part is wrong. According to the SQL standard, if a numeric value expression contains NULL, its result is NULL [2].

Browsing the SQL documentation, we see how each operator handles the NULL value. Below are some examples:
- **Comparison operator**: In a comparison operator, if any of the operands is NULL, then the result of the operator is **unknown** [3].
- **Logical operator**: There are 3 possible outcomes of a logical operator: true, false, and **unknown** [4]. Let's take a look at the truth table for the AND boolean. If the first operand is false then the result is false. In contrast, when the first operand is true then the result could be true, false, or unknown depending on the second operand.

## A mental model to interpret NULL values

On this [page](https://modern-sql.com/concept/three-valued-logic), I found an interesting method to evaluate NULL and expressions containing NULL:

- The SQL null value means "could be anything".
- If we replace NULL in an expression with 2 different values and obtain 2 different results, then the result of the expression is unknown.

It makes sense when I apply this model to my case. The result of dividing a number by a random number is unknown, or NULL.

The author also mentions a few odd consequences of NULL on the website. You should take a look.

## Conclusion
NULL and three-valued logic are critical concepts to understand. These concepts can help us evaluate logical expressions and avoid bugs. Unit tests helped me discover this new territory in SQL. Otherwise, I would have had a working code without fully understanding it.

## Reference

[1] - [Database Language SQL - 3.1.3  Definitions provided in this International Standard](https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt)
[2] - [Database Language SQL -  6.12 numeric value expression](https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt)
[3] - [Database Language SQL -   8.2 comparison predicate](https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt)
[4] - [Database Language SQL -   8.12 search condition](https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt)