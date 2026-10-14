package cz.example.perf.setup

import io.gatling.javaapi.core.ChainBuilder

data class UseCase(val name: String, val weight: Int, val chain: () -> ChainBuilder)
