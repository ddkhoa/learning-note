# Order execution in SQL - A real-case scenario

Browsing Medium, LinkedIn, and some technical blogs, I frequently saw articles talking about the execution order of an SQL query. Until recently, I primarily thought of it in terms of optimization. A classical rule is to filter rows as soon as possible in the process. However, I ran into a case where misunderstanding the execution order resulted in incorrect results.

## Recall the execution order

- **FROM**: get data from tables mentioned in the query & join them
- **WHERE**: filter *rows* based on conditions
- **GROUP** BY: group rows and compute aggregates
- **HAVING**: filter *groups* based on conditions
- **SELECT**: select the columns and apply the transform function if there are any
- **ORDER BY**: order the result

Now, let's reproduce the problem.

## The Setup

Imagine a table of sales with the following structure and data:

```sql
CREATE TABLE sales (
    category TEXT,
    location TEXT,
    quantity INT
);

INSERT INTO sales (category, location, quantity) 
VALUES 
    ('electronics', 'Paris', 10), 
    ('beauty', 'Bordeaux', 5), 
    ('beauty', 'Marseille', 10), 
    ('high-tech', 'Paris', 5), 
    ('high-tech', 'Marseille', 2);
```

I used the [CUBE]((https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-GROUPING-SETS)) keyword to calculate the number of products sold for each combination of category and location and totals for all categories, locations, and overall total.


```sql
SELECT category, location, SUM(quantity) product_sold
FROM sales 
GROUP BY CUBE(category, location);
```

## Result

|  category   | location  | product_sold |
| ----------- | --------- | ------------ |
| NULL        | NULL      | 32           |
| electronics | Paris     | 10           |
| high-tech   | Marseille | 2            |
| beauty      | Bordeaux  | 5            |
| beauty      | Marseille | 10           |
| high-tech   | Paris     | 5            |
| high-tech   | NULL      | 7            |
| beauty      | NULL      | 15           |
| electronics | NULL      | 10           |
| NULL        | Marseille | 12           |
| NULL        | Paris     | 15           |
| NULL        | Bordeaux  | 5            |

## Note

GROUP BY CUBE generates rows where NULL in a column represents totals across all values of that column. In the table above, the first rows represent the number of products sold across locations and categories.

## The Problem  

Now, consider that we insert a row into the sales table where the category is NULL:

```sql
INSERT INTO sales (category, location, quantity) 
VALUES (NULL, 'Paris', 3);
```

To replace this NULL value with a more meaningful value for example `'NA'`, you might think to use `COALESCE` in the `SELECT` clause. Here's the query:

```sql
SELECT COALESCE(category, 'NA') category, location, SUM(quantity) product_sold
FROM sales 
GROUP BY CUBE(category, location);
```

The result:

|  category   | location  | product_sold |
| ----------- | --------- | ------------ |
| NA          | NULL      | 35           |
| electronics | Paris     | 10           |
| high-tech   | Marseille | 2            |
| NA          | Paris     | 3            |
| beauty      | Bordeaux  | 5            |
| beauty      | Marseille | 10           |
| high-tech   | Paris     | 5            |
| NA          | NULL      | 3            |
| high-tech   | NULL      | 7            |
| beauty      | NULL      | 15           |
| electronics | NULL      | 10           |
| NA          | Marseille | 12           |
| NA          | Paris     | 18           |
| NA          | Bordeaux  | 5            |

Did you spot something wrong in the result? 
- The combination of ('NA', 'Paris') appears 2 times! One has 3 products sold - the number of products sold without the category. The other one has 18 products sold - the number of products sold in Paris across categories. All `NULL` values are now transformed to `NA`. We cannot distinguish whether a row is represented for the missing category or all categories.

## Why does this happen?

We apply the execution order mentioned previously in this case, here is what happened:
1. GROUP BY CUBE is executed. 
- It creates aggregations for all basic combinations, including (NULL, 'Paris').
- Then, it creates aggregations across categories, across locations, and finally the total sums. In this step, it generates the combination (NULL, 'Paris') 1 more time.

1. SELECT is executed
- The COALESCE function is applied to the category column and converts all `NULL` values to `'NA'`

As a result, the combination of ('NA', 'Paris') appears 2 times.

## What is the solution, then?

The result we want is:

|  category   | location  | product_sold |
| ----------- | --------- | ------------ |
| **NULL**    | NULL      | 35           |
| electronics | Paris     | 10           |
| high-tech   | Marseille | 2            |
| NA          | Paris     | 3            |
| beauty      | Bordeaux  | 5            |
| beauty      | Marseille | 10           |
| high-tech   | Paris     | 5            |
| high-tech   | NULL      | 7            |
| NA          | NULL      | 3            |
| beauty      | NULL      | 15           |
| electronics | NULL      | 10           |
| **NULL**    | Marseille | 12           |
| **NULL**    | Paris     | 18           |
| **NULL**    | Bordeaux  | 5            |

The value `NA` should appear only 2 times, representing the products sold in Paris and all locations without category. For that, we should apply the COALESCE function on the category column *before* the GROUP clause is executed. 

One way to archive that is by using `GROUP BY CUBE(COALESCE(category, 'NA'), location)`. The following query will produce the result mentioned above:

```sql
SELECT COALESCE(category, 'NA') category, location, SUM(quantity) product_sold FROM sales GROUP BY CUBE(COALESCE(category, 'NA'), location);
```

**Bonus**
If the `NULL` values bother you, then you can replace them with a more meaningful value, for example, `ALL`. The complete query is:

```sql
SELECT COALESCE(COALESCE(category, 'NA'), 'ALL') category, COALESCE(location, 'ALL') location, SUM(quantity) FROM sales GROUP BY CUBE(COALESCE(category, 'NA'), location);
```

The final result

| category    | location  | product_sold |
|-------------|-----------|--------------|
| ALL         | ALL       |           35 |
| electronics | Paris     |           10 |
| high-tech   | Marseille |            2 |
| NA          | Paris     |            3 |
| beauty      | Bordeaux  |            5 |
| beauty      | Marseille |           10 |
| high-tech   | Paris     |            5 |
| high-tech   | ALL       |            7 |
| NA          | ALL       |            3 |
| beauty      | ALL       |           15 |
| electronics | ALL       |           10 |
| ALL         | Marseille |           12 |
| ALL         | Paris     |           18 |
| ALL         | Bordeaux  |            5 |

## Conclusion

In this article, I present to you a real case when understanding the SQL execution order is crucial to writing the correct SQL query.