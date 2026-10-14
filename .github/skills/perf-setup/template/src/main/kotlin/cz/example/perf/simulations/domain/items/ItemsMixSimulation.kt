package cz.example.perf.simulations.domain.items

import cz.example.perf.config.Protocols
import cz.example.perf.domain.items.usecases.ItemsUseCases
import cz.example.perf.setup.MixBuilder
import cz.example.perf.setup.SimulationSetup
import io.gatling.javaapi.core.CoreDsl.scenario

class ItemsMixSimulation : SimulationSetup() {
    private val scn = scenario("Items mix").exec(MixBuilder.fromDefaults(ItemsUseCases.all))

    init {
        run(scn, Protocols.api)
    }
}
