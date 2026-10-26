package cz.example.perf.contract

import cz.example.perf.domain.items.flows.ItemsFlows
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.StringBody
import io.gatling.javaapi.core.CoreDsl.atOnceUsers
import io.gatling.javaapi.core.CoreDsl.details
import io.gatling.javaapi.core.CoreDsl.doIf
import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.core.CoreDsl.global
import io.gatling.javaapi.core.CoreDsl.group
import io.gatling.javaapi.core.CoreDsl.jsonPath
import io.gatling.javaapi.core.CoreDsl.pause
import io.gatling.javaapi.core.CoreDsl.repeat
import io.gatling.javaapi.core.CoreDsl.scenario
import io.gatling.javaapi.core.Simulation
import io.gatling.javaapi.http.HttpDsl.StringBodyPart
import io.gatling.javaapi.http.HttpDsl.header
import io.gatling.javaapi.http.HttpDsl.http
import io.gatling.javaapi.http.HttpDsl.status
import java.net.URI
import java.time.Duration

/** Actual sample browse flows plus synthetic HTTP-pattern fixtures, not a load profile. */
class ItemsHttpContractSimulation : Simulation() {
    private fun createAndRead(): ChainBuilder =
        exec(
            http("Create Item").post("/items").asJson()
                .body(StringBody("""{"name":"local-dummy-item"}"""))
                .check(status().`is`(201), jsonPath("$.id").saveAs("createdId"))
        )
            .exitHereIfFailed()
            .exec(
                http("Read Created Item").get("/items/#{createdId}")
                    .queryParam("locale", "en")
                    .check(status().`is`(200), jsonPath("$.id").isEL("#{createdId}"))
            )

    private fun polling(): ChainBuilder =
        exec(
            http("Submit Job").post("/jobs").asJson().body(StringBody("{}"))
                .check(status().`is`(202), jsonPath("$.jobId").saveAs("jobId"))
        )
            .exitHereIfFailed()
            .exec { session -> session.set("state", "pending") }
            .repeat(3).on(
                doIf { session -> session.getString("state") == "pending" }.then(
                    pause(Duration.ofSeconds(1))
                        .exec(
                            http("Poll Job").get("/jobs/#{jobId}")
                                .check(
                                    status().`in`(200, 202),
                                    jsonPath("$.state").`in`("pending", "complete"),
                                    jsonPath("$.state").saveAs("state")
                                )
                        )
                        .exitHereIfFailed()
                )
            )
            .exec { session ->
                if (session.getString("state") == "complete") session else session.markAsFailed()
            }
            .exitHereIfFailed()
            .exec(http("Job Result").get("/result").check(status().`is`(200)))

    init {
        val url = System.getProperty("contractBaseUrl")
            ?: error("Run python3 .github/scripts/check_items_http.py")
        val uri = URI(url)
        require(uri.scheme == "http" && uri.host == "127.0.0.1" && uri.port > 0)
        require(uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null)
        require(uri.path.isNullOrEmpty())

        val flows = linkedMapOf(
            "browse" to ItemsFlows.browseItems(),
            "list-failure" to ItemsFlows.browseItems(),
            "json" to createAndRead(),
            "json-wrong-id" to createAndRead(),
            "json-failure" to createAndRead(),
            "json-missing-id" to createAndRead(),
            "form" to exec(
                http("Search Form").post("/search")
                    .formParam("term", "local dummy").formParam("page", "2")
                    .check(status().`is`(200))
            ),
            "multipart" to exec(
                http("Upload File").post("/upload")
                    .bodyPart(StringBodyPart("note", "local-dummy"))
                    .bodyPart(
                        StringBodyPart("file", "local-dummy-file")
                            .fileName("local-dummy.txt").contentType("text/plain")
                    )
                    .asMultipartForm()
                    .check(status().`is`(201))
            ),
            "no-content" to exec(
                http("Update Item").put("/items/1").asJson()
                    .body(StringBody("""{"name":"local-dummy-updated"}"""))
                    .check(status().`is`(204)),
                http("Patch Item").patch("/items/1").asJson()
                    .body(StringBody("""{"name":"local-dummy-patched"}"""))
                    .check(status().`is`(204)),
                http("Delete Item").delete("/items/1").check(status().`is`(204)),
                http("Head Items").head("/items").check(status().`is`(204), header("X-Contract").`is`("local")),
                http("Options Items").options("/items").check(status().`is`(204))
            ),
            "profiles" to exec(
                http("Gateway Request").get("/gateway").header("api-key", "local-dummy-key")
                    .check(status().`is`(200)),
                http("Public Request").get("/public").check(status().`is`(200))
            ),
            "poll-complete" to polling(),
            "poll-timeout" to polling(),
            "poll-terminal" to polling()
        )
        val populations = flows.map { (name, flow) ->
            scenario(name).exec(group(name).on(flow)).injectOpen(atOnceUsers(1))
                .protocols(http.baseUrl("$url/$name").disableWarmUp().disableFollowRedirect())
        }
        setUp(populations).maxDuration(Duration.ofSeconds(15))
            .assertions(
                global().allRequests().count().`is`(27L),
                global().failedRequests().count().`is`(5L),
                details("browse", "Get Items").successfulRequests().count().`is`(1L),
                details("list-failure", "Get Items").failedRequests().count().`is`(1L),
                details("json", "Create Item").successfulRequests().count().`is`(1L),
                details("json", "Read Created Item").successfulRequests().count().`is`(1L),
                details("json-wrong-id", "Create Item").successfulRequests().count().`is`(1L),
                details("json-wrong-id", "Read Created Item").failedRequests().count().`is`(1L),
                details("json-failure", "Create Item").failedRequests().count().`is`(1L),
                details("json-missing-id", "Create Item").failedRequests().count().`is`(1L),
                details("form", "Search Form").successfulRequests().count().`is`(1L),
                details("multipart", "Upload File").successfulRequests().count().`is`(1L),
                details("no-content", "Update Item").successfulRequests().count().`is`(1L),
                details("no-content", "Patch Item").successfulRequests().count().`is`(1L),
                details("no-content", "Delete Item").successfulRequests().count().`is`(1L),
                details("no-content", "Head Items").successfulRequests().count().`is`(1L),
                details("no-content", "Options Items").successfulRequests().count().`is`(1L),
                details("profiles", "Gateway Request").successfulRequests().count().`is`(1L),
                details("profiles", "Public Request").successfulRequests().count().`is`(1L),
                details("poll-complete", "Poll Job").successfulRequests().count().`is`(2L),
                details("poll-complete", "Job Result").successfulRequests().count().`is`(1L),
                details("poll-timeout", "Poll Job").successfulRequests().count().`is`(3L),
                details("poll-terminal", "Poll Job").failedRequests().count().`is`(1L)
            )
    }
}
