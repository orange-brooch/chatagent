import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.function.Predicate;

/**
 * One domain agent (hotels, restaurants). Plays the role of one AgentCore Runtime in the lab.
 * Instead of an LLM interpreting free text, the user picks from a fixed menu of questions;
 * each question maps to a query over this agent's own table. Answers are rows from the data,
 * never generated text, so they cannot be wrong in a way the data is not.
 */
final class ScriptedAgent {
    record Option(String label, Predicate<Map<String, String>> where) {}

    private final String name;
    private final CsvTable table;
    private final List<Option> options;
    private final Function<Map<String, String>, String> format;

    ScriptedAgent(String name, CsvTable table, List<Option> options,
                  Function<Map<String, String>, String> format) {
        this.name = name;
        this.table = table;
        this.options = options;
        this.format = format;
    }

    String name() {
        return name;
    }

    List<Option> options() {
        return options;
    }

    List<String> cities() {
        return table.distinct("city");
    }

    String answer(int optionIndex) {
        return render(table.select(options.get(optionIndex).where()));
    }

    String answerForCity(String city) {
        return render(table.select(r -> r.get("city").equalsIgnoreCase(city)));
    }

    private String render(List<Map<String, String>> rows) {
        if (rows.isEmpty()) return "  (no matches in our data)";
        StringBuilder sb = new StringBuilder();
        for (Map<String, String> row : rows) sb.append("  - ").append(format.apply(row)).append('\n');
        return sb.toString().stripTrailing();
    }
}
