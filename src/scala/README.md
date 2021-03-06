# Tracker Commons Scala Reference Implementation

This project contains source code in Scala that implements the WCON data
format for tracking data.  When the text specification and the behavior of
the Scala implementation differ, and it is not obvious which one is correct,
the behavior of the Scala implementation should be presumed to be authoritative.

## Requirements

This project requires Java 8 and [Scala 2.11](http://scala-lang.org).  You do
not need to install Scala explicitly, as the build process is managed by
[SBT](http://www.scala-sbt.org/).  SBT must be installed to build the project,
and it will take care of downloading Scala and any needed libraries.

## Building the project

Type `sbt package` in this directory.  SBT will tell you where it has
created the jar file.  You can include this jar in your classpath.

## Using the reference implementation to read worm data

Here is an example of reading WCON data with the Scala implementation.
This example is meant to run in the SBT console (`sbt console` from the
command prompt, when within the `src/scala` directory).  The `scala`
REPL works just as well if you put the TrackerCommons jar file on the
classpath.

```scala
import org.openworm.trackercommons._
val worms = ReadWrite.read("../../tests/intermediate.wcon") match {
  case Right(ws) => ws
  case Left(err) => println(err); throw new Exception
}
```

The `ReadWrite` object will attempt to read a data file, delivering an
error message if it cannot.  The code above extracts the correct data if
there (the `Right` case), and prints the error and throws an exception if
not.  (If you don't care about error-handling, replace the `match` and following
statements with `.right.get`.)

The Scala reader/writer does its best to preserve the underlying structure
of the data file.  However, this may not be the most convenient form in which
to browse the data.  The `DataSet` class can extract and merge all the data
by ID, using the `combined()` method.  This method can take a map of functions
that are used to merge data from custom tags, and these functions may fail,
so the entire operation may fail.  Thus, the function returns an `Either`, from
which you can extract your data:

```scala
val data = worms.combined() match {
  case Right(ds) => ds
  case Left(err) => println(err); throw new Exception
}
```

You should see something like so (except formatted on a single line):

```
res0: Array[org.openworm.trackercommons.Data] =
  Array({ "id": 1, "ox": [0.6, 0.9], "oy": [0, -0.04], "t": [0, 1],
      "x": [ [-0.6, -0.3, 0, 0.3, 0.6], [-0.6, -0.3, 0, 0.3, 0.6] ],
      "y": [ [0, -0.2, 0, 0.2, 0], [-0.16, 0.04, 0.24, 0.04, -0.16] ] },
    { "id": 2, "ox": [0], "oy": [1.5], "t": [1], "x": [ [0, 0.2, 0, -0.2, 0] ],
      "y": [ [-0.5, -0.25, 0, 0.25, 0.5] ] })
```

## Running project tests

Type `sbt test` in this directory.  The test suite will run, which mostly
involves reading basic and advanced sample files, writing them, and checking
that the output is as expected.

## What does it mean for the Scala implementation to be the "Reference Implementation?"

The Tracker Commons code repository will contain code for a variety of languages
that may be used to read and write WCON files.  The behavior of all of these
should be identical.  Common sense should be used when output disagrees as to
which implementation is correct, but if it is not obvious the Scala version
is considered to have the "correct behavior".

#### What if implementations and/or the spec disagree?

Submit a bug report, or make a pull request with a fix!  Unless the implmentation
is documented to be incomplete, any differences from specification are bugs.

#### Why Scala?

1. Scala's strong typing and functional approach makes it easier to ensure
that code is correct.

2. There are parsing libraries available that compactly represent the logic
of what you are trying to parse.  This makes the gap between text and code
especially small, which is an advantage when trying to keep the two
synchronized.

3. Rex wrote this code, and he knows Scala well and likes it.
