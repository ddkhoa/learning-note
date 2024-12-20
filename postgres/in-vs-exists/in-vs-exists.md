- IN can be followed by a list of values or a subquery
- EXISTS can be followed by a subquery only

When a subquery follows these 2 keywords:
- In some cases, queries using IN and EXISTS keywords generate the same execution plan.

- Using EXISTS with correlated conditions **forces** Postgres to execute the outer part first. For each value of the outer part, the subquery (inside EXISTS) is executed.
  - Good when the outer part is small and the subquery is fast (selective condition)
  - Question: When the outer part is big -> big loop -> worse ?
  
- Using IN gives Postgres more room for optimization. (Postgres does a lot of optimization behind the scenes)
  - If it sees a branch gives 0 rows (query being already executed, **runtime**), other branches can be abandoned (marked as "never executed" in the execution plan)
  - Question: Can Postgres determine the right order for Nested Loop Join based on the row number of left & right relation?
    - Smaller relation is the outer -> fewer loops on the inner relation? (in the previous point, 0 is a special case).

- For both IN and EXISTS, the subquery should have the right condition to be executed quickly.
