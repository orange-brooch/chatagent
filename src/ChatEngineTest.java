import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Dependency-free tests. Run: java -cp out ChatEngineTest (exit code 1 on failure). */
public class ChatEngineTest {
    private static int failures = 0;
    private static final Path DATA = Path.of("data");

    public static void main(String[] args) throws IOException {
        menuListsAgentsAndTrip();
        hotelAnswersMatchDatabaseExactly();
        restaurantAnswerIsOnlyRealRows();
        invalidInputKeepsUserInPlace();
        tripMergesBothAgents();
        tripDegradesWhenOneAgentIsDown();
        quitEndsConversation();
        System.out.println(failures == 0 ? "\nALL TESTS PASSED" : "\n" + failures + " TEST(S) FAILED");
        System.exit(failures == 0 ? 0 : 1);
    }

    static void menuListsAgentsAndTrip() {
        String menu = Main.buildEngine(DATA).start();
        check("main menu lists both agents and trip planner",
                menu.contains("Hotel Agent") && menu.contains("Restaurant Agent") && menu.contains("Plan a trip"));
    }

    /** Correctness: the reply must contain exactly the rows an independent query returns. */
    static void hotelAnswersMatchDatabaseExactly() {
        ChatEngine engine = Main.buildEngine(DATA);
        engine.start();
        engine.handle("1");
        String reply = engine.handle("1"); // budget stays
        List<String> expected = new ArrayList<>();
        List<String> all = new ArrayList<>();
        for (Map<String, String> r : new CsvTable(DATA.resolve("hotels.csv")).select(x -> true)) {
            all.add(r.get("name"));
            if (Double.parseDouble(r.get("price")) < 150) expected.add(r.get("name"));
        }
        boolean exact = true;
        for (String name : all) exact &= reply.contains(name) == expected.contains(name);
        check("budget hotels reply == rows where price < 150 (and nothing else)", exact && !expected.isEmpty());
    }

    static void restaurantAnswerIsOnlyRealRows() {
        ChatEngine engine = Main.buildEngine(DATA);
        engine.start();
        engine.handle("2");
        String reply = engine.handle("1"); // vegetarian
        check("vegetarian list has Mesa Taqueria and Saguaro Sushi, not Cactus Table",
                reply.contains("Mesa Taqueria") && reply.contains("Saguaro Sushi") && !reply.contains("Cactus Table"));
    }

    static void invalidInputKeepsUserInPlace() {
        ChatEngine engine = Main.buildEngine(DATA);
        engine.start();
        engine.handle("1");
        String reply = engine.handle("banana");
        check("invalid input shows an error and re-shows the Hotel Agent menu",
                reply.contains("Please enter a number") && reply.contains("Hotel Agent - choose a question"));
        check("out-of-range input is rejected", engine.handle("99").contains("Please enter a number"));
    }

    static void tripMergesBothAgents() {
        ChatEngine engine = Main.buildEngine(DATA);
        engine.start();
        String cities = engine.handle("3");
        check("trip planner lists cities from the data", cities.contains("Scottsdale") && cities.contains("Sedona"));
        String reply = engine.handle("2"); // Scottsdale
        check("trip for Scottsdale merges hotel and restaurant rows",
                reply.contains("Camelback Lodge") && reply.contains("Cactus Table") && !reply.contains("Sedona Red Rock"));
    }

    static void tripDegradesWhenOneAgentIsDown() throws IOException {
        Path dir = Files.createTempDirectory("chat-data");
        Files.copy(DATA.resolve("hotels.csv"), dir.resolve("hotels.csv")); // no restaurants.csv
        ChatEngine engine = Main.buildEngine(dir);
        engine.start();
        engine.handle("3");
        String reply = engine.handle("2"); // Scottsdale
        check("restaurant table missing: hotels still answered, restaurants reported unavailable",
                reply.contains("Camelback Lodge") && reply.contains("Restaurant Agent:\n  unavailable"));
    }

    static void quitEndsConversation() {
        ChatEngine engine = Main.buildEngine(DATA);
        engine.start();
        engine.handle("q");
        check("q ends the conversation", engine.isDone());
    }

    private static void check(String name, boolean ok) {
        System.out.println((ok ? "PASS  " : "FAIL  ") + name);
        if (!ok) failures++;
    }
}
