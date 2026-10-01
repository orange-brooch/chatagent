import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * The orchestrator (the lab's supervisor). A small state machine over numbered menus:
 *   MAIN  -> pick an agent, or "plan a trip"
 *   AGENT -> pick one of that agent's scripted questions
 *   TRIP  -> pick a city; every agent answers for it and the replies are merged
 * Input and output are plain strings, so the engine is testable without a terminal.
 */
final class ChatEngine {
    private enum State { MAIN, AGENT, TRIP }

    private final List<ScriptedAgent> agents;
    private State state = State.MAIN;
    private ScriptedAgent current;
    private List<String> tripCities = List.of();
    private boolean done = false;

    ChatEngine(List<ScriptedAgent> agents) {
        this.agents = agents;
    }

    boolean isDone() {
        return done;
    }

    String start() {
        return mainMenu();
    }

    String handle(String input) {
        String in = input.trim();
        if (in.equalsIgnoreCase("q")) {
            done = true;
            return "Goodbye!";
        }
        return switch (state) {
            case MAIN -> onMain(in);
            case AGENT -> onAgent(in);
            case TRIP -> onTrip(in);
        };
    }

    private String onMain(String in) {
        int n = parse(in, agents.size() + 1);
        if (n < 0) return invalid(agents.size() + 1) + "\n" + mainMenu();
        if (n == agents.size() + 1) return startTrip();
        current = agents.get(n - 1);
        state = State.AGENT;
        return agentMenu();
    }

    private String onAgent(String in) {
        if (in.equals("0")) return backToMain();
        int n = parse(in, current.options().size());
        if (n < 0) return invalid(current.options().size()) + "\n" + agentMenu();
        String answer;
        try {
            answer = current.answer(n - 1);
        } catch (RuntimeException e) {
            answer = "  Sorry, the " + current.name() + " is unavailable right now.";
        }
        return current.options().get(n - 1).label() + ":\n" + answer + "\n\n" + agentMenu();
    }

    private String startTrip() {
        LinkedHashSet<String> cities = new LinkedHashSet<>();
        for (ScriptedAgent agent : agents) {
            try {
                cities.addAll(agent.cities());
            } catch (RuntimeException e) {
                // one agent being down must not stop the others from contributing
            }
        }
        if (cities.isEmpty()) return "No city data available right now.\n" + mainMenu();
        tripCities = new ArrayList<>(cities);
        state = State.TRIP;
        StringBuilder sb = new StringBuilder("Which city?\n");
        for (int i = 0; i < tripCities.size(); i++) sb.append("  ").append(i + 1).append(") ").append(tripCities.get(i)).append('\n');
        return sb.append("  0) Back").toString();
    }

    private String onTrip(String in) {
        if (in.equals("0")) return backToMain();
        int n = parse(in, tripCities.size());
        if (n < 0) return invalid(tripCities.size()) + "\n" + startTrip();
        String city = tripCities.get(n - 1);
        StringBuilder sb = new StringBuilder("Trip options for " + city + ":\n");
        for (ScriptedAgent agent : agents) {
            sb.append(agent.name()).append(":\n");
            try {
                sb.append(agent.answerForCity(city));
            } catch (RuntimeException e) {
                sb.append("  unavailable right now");
            }
            sb.append("\n");
        }
        return sb.append("\n").append(backToMain()).toString();
    }

    private String backToMain() {
        state = State.MAIN;
        current = null;
        return mainMenu();
    }

    private String mainMenu() {
        StringBuilder sb = new StringBuilder("What would you like to do?\n");
        for (int i = 0; i < agents.size(); i++) sb.append("  ").append(i + 1).append(") ").append(agents.get(i).name()).append('\n');
        sb.append("  ").append(agents.size() + 1).append(") Plan a trip (hotels + restaurants by city)\n");
        return sb.append("  q) Quit").toString();
    }

    private String agentMenu() {
        StringBuilder sb = new StringBuilder(current.name() + " - choose a question:\n");
        List<ScriptedAgent.Option> options = current.options();
        for (int i = 0; i < options.size(); i++) sb.append("  ").append(i + 1).append(") ").append(options.get(i).label()).append('\n');
        return sb.append("  0) Back").toString();
    }

    private static String invalid(int max) {
        return "Please enter a number from 1 to " + max + ", or q to quit.";
    }

    /** Returns 1..max, or -1 when the input is not a valid choice. */
    private static int parse(String in, int max) {
        try {
            int n = Integer.parseInt(in);
            return n >= 1 && n <= max ? n : -1;
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
