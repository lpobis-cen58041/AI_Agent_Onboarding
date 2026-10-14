package cz.example.perf.auth

import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.exec

object Auth {
    /** Copies the feeder column "token" to the session and ends the user if it is missing. */
    fun withTokenFromSession(): ChainBuilder =
        exec { session ->
            if (session.contains("token")) session.set("apiToken", session.getString("token")) else session
        }.exitHereIf { session -> session.getString("apiToken").isNullOrBlank() }
}
