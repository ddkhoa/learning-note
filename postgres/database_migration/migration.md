## Database Migration

### Purpose
In software development, code is not the only thing that changed overtime. More precisely, the business requirements changes overtime and code is one unit that is impacted. The database structure is another important unit that undergo the same modification.

In this article, we present to you how to migrate the structure of a PostgreSQL database and some good practices to adopt.
To demonstrate the concept, we use **alembic** - a Python library for database migration. General good practices don't depend on a specific tool, though.

### Example of database migration using Alembic
We start a new project and install necessary libraries

```bash
mkdir -p ~/data/my_new_project
cd ~/data/my_new_project
python -m venv env
source env/bin/activate
pip install alembic psycopg2
alembic init alembic
```

Time to create the first table. Of course, we don't want to manually create it on different environments. Instead, we create a script for that:

```bash
alembic revision -m "First migration"
```

Alembic generate an empty file in the folder `./alembic/versions`. In this file, we define the table structure:

```python
...
def upgrade() -> None:
    op.create_table(
        "test",
        sa.Column("id", sa.Integer, primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("test")

```

To apply the migration on a local machine, we need to change the value of `sqlalchemy.url` in `alembic.ini` file to point to our local database. Then, we run this command:
```bash
alembic upgrade head
```

We go to the database, the table is created! We also notice a table `alembic`. It is created by alembic to store the current version.

In the following section, we present to you some good practices in database migration.

### Prevent information scattered
Each migration file represent the different between 2 database version. Overtime, the database structure is scattered. It is difficult to find the information of a specific object. Example: A column was created in 1 migration but then is renamed and even change the datatype.

In `alembic`, we can avoid this problem using the `autogenerate` feature. Notice this comment in the file `env.py`:
```python
# add your model's MetaData object here
# for 'autogenerate' support
```

To use this feature, we define tables we want in a `model` file. 

```python
# model.py

from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import INTEGER

Base = declarative_base()
metadata = Base.metadata

class TestTable(Base):
    __tablename__ = "test"
    id = Column(INTEGER(), primary_key=True)

```

In the `env.py` file, we modify the code to retrieve `target_metadata` from the `model` file

```python
# add your model's MetaData object here
# for 'autogenerate' support

import model
target_metadata = model.metadata
```

When generate a revision, we add the parameter `autogenerate` in the command. 
```bash
 alembic revision -m "First migration" --autogenerate
```

Alembic will compare the difference between the model file and the database current state. Then it generates the migration file with the commands to fill the difference.

This is not a handy feature in `alembic`, but can also help us to centralize the database information in 1 place. It is easier to find the type of a specific column or verify if an index exists. 

Important: if you already define the table structure in `model` file and don't use the `autogenerate` feature yet, you should adopt it. Why? Defining the table structure in 2 places (the model file and the migration file) creates **two** sources of truth. We can forget to update a column type in `model` file after changing it in a migration. By using `autogenerate` feature, we only need to maintain the `model` file properly.  

### Include the maximum information in model file
In the previous section, we defined the table structure by a class in `model` file. It's good, but not enough. In the database, we have various information:
- index
- constraints
- enum
- partition info if any

The goal is to have the maximum information in the model file so it becomes a reliable source of database information.

#### Index
Index can be defined as table arguments, for example:

```python
class TestTable(Base):
    __tablename__ = "test"
    id = Column(INTEGER(), primary_key=True)
    name = Column(TEXT(), nullable=False)
    enum_field = Column(ENUM(MyEnum))

    __table_args__ = (
        Index(
            "test_name_idx",
            name,
        ),
    )

```
When you generate the migration file, Alembic autogenerates the line to create the index.

#### Enum
Enum is convenient for a column with some static values. Enum column doesn't require join operators to have meaningful names and provides a check when inserting the data.
If an enum column appears in 2 different tables, we want to use the same enum type. The worst case scenario is when we use the same enums under different names (so technically they are 2 different enums in the database) for 2 columns. It is very likely to have the following issues:

  - Query performance
Index scan doesn't work when casting.

  - Alter column type locks the table
When we realize that 2 columns uses different enums which represent the same concept, we want to convert 1 column to the type used by other. We run the following queries:

```sql
@TODO: Alter
``` 

These 2 commands will **block** the table for a while, no one can read or write the table during that time. Because these commands rewrite the entire table. Converting a enum column on a large table isn't easy task.
It's better to avoid these issues than dealing with them. Unfortunately, `alembic` doesn't provide a mechanism to reuse an enum defined in model file.

If we add the following table in the model file:
```python
class TestTable2(Base):
    __tablename__ = "test2"
    id = Column(INTEGER(), primary_key=True)
    email = Column(TEXT(), nullable=False)
    enum_field = Column(ENUM(MyEnum))

    __table_args__ = (
        Index(
            "test_name_idx",
            name,
        ),
    )

```
The `enum_field` in this table is the same with the column in the table `test` mentioned previously. However, when generate a migration file, alembic tries to recreate the enum:
```python
def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('test2',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('email', sa.TEXT(), nullable=False),
    sa.Column('enum_field', postgresql.ENUM('one', 'two', 'three', name='myenum'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('test2')
    # ### end Alembic commands ###

```

When running the command `alembic upgrade head`, we have the error `type "myenum" already exists`. If we define a new class `MyEnum2` and use it in the column `enum_field`, the migration will work but we are in the worst case scenario mentioned previously.

Good news, the package [alembic_postgresql_enum](https://pypi.org/project/alembic-postgresql-enum/) solves this problem for us. We need to install the library in our project then import it in `env.py` file.

In the migration generated using this plugin, alembic creates the enum before using it to define the column (notice the parameter `create_type = False` when creating the column)

```python
    ...
    sa.Enum('one', 'two', 'three', name='myenum').create(op.get_bind())
    op.create_table('test',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('name', sa.TEXT(), nullable=False),
        sa.Column('enum_field', postgresql.ENUM('one', 'two', 'three', name='myenum', create_type=False), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    ...
```

The enum `myenum` can be reused in the future migrations.

### Partition info



We can have 2 columns in 2 tables, having the same enum type.
-> Work in the same migration but if we do the same thing in a following migration, it doesn't work
The database has 1 enum
