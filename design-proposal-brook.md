# sqlalchemy-redshift: SQLAlchemy 2.0 Support Design 

# Background

## What is SQLAlchemy?

SQLAlchemy is a Python package that provides an Object Relational Mapping (ORM) for working with database objects in the Python programming language. 

SQLAlchemy defines a “dialect” as a bridge between SQLAlchemy and a database driver which implements the DB-API specification.

The Redshift drivers/client team maintains sqlalchemy-redshift, which is a SQLAlchemy dialect for Amazon Redshift. It uses our Redshift Python driver, redshift-connector. 

Redshift competitors such as Snowflake, Databricks, and Google BigQuery maintain SQLAlchemy dialects for their respective products.


## Why do we have a SQLAlchemy dialect?

While SQLAlchemy provides native support for Postgres, it does not for Amazon Redshift. There are many differences between Postgres and Amazon Redshift which present themselves through SQLAlchemy.

1. IAM and IdP authentication
2. Support for Amazon Redshift datatypes such as `GEOMETRY`, `SUPER`

In summary a SQLAlchemy dialect for Amazon Redshift allows SQLAlchemy customers to leverage all of the benefits of our Redshift specific driver.

The Redshift clients/driver team became involved with sqlalchemy-redshift in 2021 through pursuit to develop an Apache Airflow provider and native support for Querybook.

[Apache Airflow Redshift Provider Scoping](https://quip-amazon.com/g1MuAGK9Idbk)
[Redshift providing a native integration with QueryBook](https://quip-amazon.com/IN7GAXMmWwUh)

## How do Amazon Redshift customers use SQLAlchemy?

* In Python programs or interactive notebooks e.g. Jupyter
* Via Apache Airflow
* Via Querybook
* Via any other Python packages which leverages SQLAlchemy

See the following blog for example code showing how to leverage sqlalchemy-redshift. https://aws.amazon.com/blogs/big-data/use-the-amazon-redshift-sqlalchemy-dialect-to-interact-with-amazon-redshift/


# Problem Statement

In January 2023, SQLAlchemy release major version 2.0. As such, SQLAlchemy 1.4, the previous major version, is officially in maintenance mode and considered legacy.

Our SQLAlchemy dialect for redshift, sqlalchemy-redshift, supports SQLAlchemy 1.4. GitHub customers of sqlalchemy-redshift have long requested SQLAlchemy 2.0 support, see [GitHub issue #264](https://github.com/sqlalchemy-redshift/sqlalchemy-redshift/issues/264). Additionally, customers such as Stanson Health are requesting support.

SQLAlchemy 2.0 [contains significant API changes](https://www.sqlalchemy.org/blog/2023/01/26/sqlalchemy-2.0.0-released/) compared to SQLAlchemy 1.4. Adding support for SQLAlchemy 2.0 to a dialect is non-trivial with the SQLAlchemy project providing two guides ([1](https://docs.sqlalchemy.org/en/latest/changelog/migration_20.html)) ([2](https://docs.sqlalchemy.org/en/latest/changelog/whatsnew_20.html)) for preforming the migration.

Below are a few customer excerpts on why SQLAlchemy 2.0 support is desired:

*“For our use cases, I think our biggest is around a strong desire to be on the up to date dependencies. We're continuously writing new code, and it'd be incredibly beneficial for us to be able to write that code using the new 2.x setup rather than having to write more code in 1.4 that will just have to be refactored once we can use 2.x. There's also many performance benefits to 2.x that could have significant potential impacts on our web app that heavily utilizes our redshift warehouse, especially around improved async support in 2.x. It's also important for us to be on the more up to date versions for the improved security that comes along with it.“ -* ***Stanson Healthe***

“*A key requirement we have for our data warehouse solution is robust and up-to-date support for widely used languages and libraries like Python and SqlAlchemy.  It is important for the long-term security, performance, and maintainability of our platform that our warehouse provider is committed to supporting these tools.  As* *I mentioned on the call today, the lack of a Sqlalchemy 2.0 Redshift dialect library is a pain point for my team.  All other dialects we use have 2.0 support today, however we are unable to fully transition our platform due to our need to interact with Redshift.”* - ***Stanson Health***

*“We’ve really loved and been impressed with redshift. We’re also looking to do some cleanup and dependency updates, but unfortunately it seems like sqlalchemy-reshift keeps us pegged to an older version of sqlalchemy, and we’d like to get to current, which I believe is 2.X . ” - **Premier Inc.***

Customer SPIEGEL-Verlag Rudolf Augstein GmbH & Co KG is working on modernizing and optimizing their BI Solutions based on Amazon Redshift stating: “*AWS, could you please give us an estimate on when the Redshift dialect for SQLAlchemy will support version 2.0 of SQLAlchemy? We have been wanting to upgrade to SQLAlchemy 2.0 for a while now and our modernization project is partly blocked by this.” -* ***Sebastian Schröder - Spiegel***


*IHAC who is using SQLAlchemy with Redshift. However, they are starting to run into issues because the [Redshift driver for SQLAlchemy](https://github.com/sqlalchemy-redshift/sqlalchemy-redshift) is outdated and don't support the latest versions of python or SQLAlchemy. There are issues open to support the modern versions of SQLAlchemy ( https://github.com/sqlalchemy-redshift/sqlalchemy-redshift/issues/264 ) but it seems to be stalled. Do we have a timeline on when this issue will be resolved or the drivers wills be updated to support SQLAlchemy 2.0? And in the meantime, are there any alternatives for this?* — **BlueLabs**

# Benefits

* SQLAlchemy 1.4 will stop receiving security updates at some point (no ETA given), and we will be forced to update eventually.
* [Improved performance](https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#major-architectural-performance-and-api-enhancements-for-database-reflection)
* Competitive advantage: SQLAlchemy 2.0 support is something our competitors have yet to implement despite customer demand (see [How have Redshift competitors handled this?](https://quip-amazon.com/abnIAqgTT6tP#temp:C:bFf2a15977c7f124521a00d9e8c2) to review GitHub customers requesting this feature for our competitor’s SQLAlchemy dialects)

# Blocking Issues

* Major decisions, such as whether to move strictly to SQLAlchemy 2.0 support or to support both 2.0 and 1.4 in parallel need to be discussed. **Preferably we should directly raise this question to our customers as their opinions should be a key driver in our path forward.**

# Design

## Considerations

#### Backwards Compatibility

Not all sqlalchemy-redshift customers will want to/be ready to migrate to SQLAlchemy 2.0. As such, maintaining backwards compatibility with SQLAlchemy 1.4, the currently supported SQLAlchemy version in sqlalchemy-redshift, is the most customer friendly option. 

We should always prefer to introduce backwards compatible changes and features to avoid breaking our customers existing workflows when possible.


#### Testing

Supporting a heavily reworked API will require substantial testing effort in our SQLAlchemy dialect to ensure the SQLAlchemy API methods we implement in our dialect comply with the API specification. This is a great opportunity to improving the testing posture of this inherited package and raise our quality bar to prevent the introduction of regressions down the road.

The existing test suite, which was written for SQLAlchemy 1.4 support, can be leveraged to gain confidence in backwards compatibility if we choose to provide backwards compatibility.


#### Versioning

Python customers are particular about the use of [semantic versioning](https://semver.org/). To avoid breaking customer trust we must ensure we are precise in how we choose to version the release which contains SQLAlchemy 2.0 support. 

The most conservative approach is to apply a major version upgrade regardless of which approach we take to implement SQLAlchemy 2.0 support. This would ensure customers migrating to this new major version of our package do so intentionally and are not surprised by potential incompatibilities.

If we choose to maintain backwards compatibility for SQLAlchemy 1.4 and maintain a high bar for test coverage, we can confidently choose to apply a minor version upgrade for the release.

#### Transparency with our Community

If possible, we should iteratively implement SQLAlchemy 2.0 support in the public domain. This means developing using a GitHub branch associated with a draft PR. This will allow our customers and community to frequently give us feedback and have confidence that this migration is being actively worked. Providing customers transparency into the changes that happen in a project is an essential part of what open source is all about.

Allowing our customers to raise concerns with the draft changes early will allow the Redshift clients and drivers team to proactively address potential issues as well have access to a large number of active community members who are willing to provide feedback.


## [Preferred] Maintain backwards compatibility with SQLAlchemy 1.4

**Pros**

* Satisfies customer requests for SQLAlchemy 2.0.
* Customers using SQLAlchemy 1.4 continue to receive support.
* Delays bumping the major version of sqlalchemy-redshift until a TBD date we entirely drop SQLAlchemy 1.4 support
* Partner product, Apache Airflow, is taking this same approach. See [discussion here](https://github.com/apache/airflow/issues/28723#issuecomment-1371038430).

**Cons**

* Requires additional implementation and testing effort to ensure backwards compatibility.
* Requires deprecation plan for SQLAlchemy 1.4 support.
* More complex code to account for supporting the significant API changes in SQLAlchemy 2.0.
* (Bit of an assumption here) If customers are using an old version of SQLAlchemy, who says they are using latest version of sqlalchemy-redshift. Our efforts for friendliness may be moot.



## Only support SQLAlchemy 2.0

**Pros**

* Cleaner code as we would only support 1 major version of SQLAlchemy.
* Faster delivery as we do not need to worry about backwards compatibility.
* Introducing a major version bump leaves us fewer qualms about introducing breaking changes.

**Cons**

* Customers using SQLAlchemy 1.4 will no longer be able to receive support, including security updates.
* A major version bump would be required for sqlalchemy-redshift, making consumption.

## Comparative Analysis

### *How have other SQLAlchemy dialects handled this?* 

tl;dr most all actively maintained dialects have added support. It varies whether they provide backwards compatibility with SQLAlchemy 1.4.


### *How have Redshift competitors handled this?*

tl;dr they haven’t added SQLAlchemy 2.0 support yet. Adding support is a competitive advantage for Redshift.


***How have the products sqlalchemy-redshift integrates with handled this?***


# Work Estimate


# Cross-Design Implementation Plan

The below implementation plan lays out high level steps we must preform to add SQLAlchemy 2.0 support regardless of whether we choose to provide backwards compatibility for SQLAlchemy 1.4.


*Summarized from the [SQLAlchemy 2.0 migration guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#). The below steps are to be preformed with SQLAlchemy 1.4. Tests will be added as changes are made during the migration process.*

1. Determine code coverage basis
2. Ensure no deprecation warnings are seen when running sqlalchemy-redshift with SQLAlchemy 1.4.
    1. Refactor statements which emit a deprecation warning.
3. [The URL object is now immutable](https://docs.sqlalchemy.org/en/20/changelog/migration_14.html#change-5526) 
    1. Refactor statements mutating the URL object.
4. [A SELECT statement is no longer implicitly considered to be a FROM clause](https://docs.sqlalchemy.org/en/20/changelog/migration_14.html#change-4617) 
    1. Analyze usage patterns of SELECT and refactor
5. [select().join() and outerjoin() add JOIN criteria to the current query, rather than creating a subquery](https://docs.sqlalchemy.org/en/20/changelog/migration_14.html#change-select-join) 
    1. Analyze usage patterns of JOIN and refactor
6. [Many Core and ORM statement objects now perform much of their construction and validation in the compile phase](https://docs.sqlalchemy.org/en/20/changelog/migration_14.html#change-deferred-construction) 
    1. Visually inspect where exceptions are caught/raised in sqlalchemy-redshift and determine if exception handling logic needs refactor
7. Turn on RemovedIn20Warnings
    1. Refactor statements which emit a deprecation warning
8. ** **Use the** **`future`** **flag on Engine
    1. Resolve all warnings and errors raised when test suite is run
9. Use the** **`future`** **flag on Session
    1. Resolve all warnings and errors raised when test suite is run
10. Add** **`__allow_unmapped__`** **to explicitly typed ORM models
    1. Should mainly apply to our test suite


*The below steps are to be preformed with SQLAlchemy 2.0. New tests will be added for any changes made during SQLAlchemy 2.0 testing.*

1. Test against a SQLAlchemy 2.0 Release
    1. Analyze test failures and determine if they are regressions or tests needing adjustment

