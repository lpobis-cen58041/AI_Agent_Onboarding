package cz.example.perf.testutil

/** csv() feeders need a Gatling configuration that the launcher normally sets; unit tests set it here. */
object GatlingTestBootstrap {
    @Volatile
    private var initialized = false

    @Synchronized
    fun init() {
        if (initialized) return

        @Suppress("UNCHECKED_CAST")
        val noOverrides = scala.collection.immutable.`Nil$`.`MODULE$`
            as scala.collection.immutable.Seq<scala.Tuple2<String, *>>
        val configuration = io.gatling.core.config.`GatlingConfiguration$`.`MODULE$`.loadForTest(noOverrides)
        io.gatling.core.`Predef$`.`MODULE$`.`_configuration_$eq`(configuration)
        initialized = true
    }
}
