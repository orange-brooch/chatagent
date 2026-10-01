import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

public class Main {
    /** Wires the two agents to their tables. Tests build engines through here too. */
    static ChatEngine buildEngine(Path dataDir) {
        ScriptedAgent hotels = new ScriptedAgent(
                "Hotel Agent",
                new CsvTable(dataDir.resolve("hotels.csv")),
                List.of(
                        new ScriptedAgent.Option("Budget stays (under $150/night)", r -> price(r) < 150),
                        new ScriptedAgent.Option("Spa hotels", r -> hasTag(r, "spa")),
                        new ScriptedAgent.Option("Close to hiking", r -> hasTag(r, "hiking")),
                        new ScriptedAgent.Option("Hotels with a pool", r -> hasTag(r, "pool"))),
                r -> r.get("name") + " - " + r.get("city") + " - $" + r.get("price") + "/night");

        ScriptedAgent restaurants = new ScriptedAgent(
                "Restaurant Agent",
                new CsvTable(dataDir.resolve("restaurants.csv")),
                List.of(
                        new ScriptedAgent.Option("Vegetarian-friendly", r -> hasTag(r, "vegetarian")),
                        new ScriptedAgent.Option("Under $20 per person", r -> price(r) < 20),
                        new ScriptedAgent.Option("Dinner spots", r -> hasTag(r, "dinner")),
                        new ScriptedAgent.Option("Breakfast spots", r -> hasTag(r, "breakfast"))),
                r -> r.get("name") + " (" + r.get("cuisine") + ") - " + r.get("city") + " - $" + r.get("price") + " pp");

        return new ChatEngine(List.of(hotels, restaurants));
    }

    private static double price(Map<String, String> row) {
        return Double.parseDouble(row.get("price"));
    }

    private static boolean hasTag(Map<String, String> row, String tag) {
        return List.of(row.get("tags").split("\\|")).contains(tag);
    }

    public static void main(String[] args) throws IOException {
        ChatEngine engine = buildEngine(Path.of(args.length > 0 ? args[0] : "data"));
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        System.out.println(engine.start());
        while (!engine.isDone()) {
            System.out.print("\n> ");
            String line = in.readLine();
            if (line == null) break;
            System.out.println(engine.handle(line));
        }
    }
}
