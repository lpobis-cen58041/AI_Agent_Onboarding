package cz.example.perf.config

object Config {
    private fun prop(name: String): String? = System.getProperty(name) ?: System.getenv(name)

    val baseUrl: String = prop("baseUrl")?.trim()?.takeIf { it.isNotBlank() } ?: "http://localhost:8080"
    val apiKey: String = prop("apiKey") ?: "dummy-key"
    val durationSeconds: Long = prop("durationSec")?.toLong() ?: 30
    val usersPerSecond: Double = resolveUsersPerSecond(::prop)
    @Deprecated("This is a virtual-user arrival rate, not HTTP RPS. Use usersPerSecond.")
    val targetRps: Double get() = usersPerSecond
    val maxFailedPercent: Double = prop("maxFailedPercent")?.toDouble() ?: 1.0
}

internal fun resolveUsersPerSecond(property: (String) -> String?): Double {
    val raw = property("usersPerSecond") ?: property("targetRps") ?: "2.0"
    val rate = raw.toDoubleOrNull()
    require(rate != null && rate.isFinite() && rate > 0) {
        "usersPerSecond (legacy: targetRps) must be a finite number greater than zero; got '$raw'"
    }
    return rate
}
