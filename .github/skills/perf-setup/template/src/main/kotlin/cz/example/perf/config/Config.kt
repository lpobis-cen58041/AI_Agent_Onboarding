package cz.example.perf.config

object Config {
    private fun prop(name: String): String? = System.getProperty(name) ?: System.getenv(name)

    val baseUrl: String = prop("baseUrl")?.trim()?.takeIf { it.isNotBlank() } ?: "http://localhost:8080"
    val apiKey: String = prop("apiKey") ?: "dummy-key"
    val durationSeconds: Long = prop("durationSec")?.toLong() ?: 30
    val targetRps: Double = prop("targetRps")?.toDouble() ?: 2.0
    val maxFailedPercent: Double = prop("maxFailedPercent")?.toDouble() ?: 1.0
}
