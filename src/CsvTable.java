import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Stand-in for a database table (the lab reads from S3).
 * Re-reads the file on every query, the way a DB read hits storage, so a missing
 * or broken table surfaces as an exception the router has to handle.
 * To use a real database, replace select() with a JDBC query; nothing else changes.
 */
final class CsvTable {
    private final Path path;

    CsvTable(Path path) {
        this.path = path;
    }

    List<Map<String, String>> select(Predicate<Map<String, String>> where) {
        List<Map<String, String>> rows = new ArrayList<>();
        try {
            List<String> lines = Files.readAllLines(path);
            String[] header = lines.get(0).split(",");
            for (String line : lines.subList(1, lines.size())) {
                if (line.isBlank()) continue;
                String[] cells = line.split(",", -1);
                Map<String, String> row = new LinkedHashMap<>();
                for (int i = 0; i < header.length; i++) {
                    row.put(header[i].trim(), i < cells.length ? cells[i].trim() : "");
                }
                if (where.test(row)) rows.add(row);
            }
        } catch (IOException e) {
            throw new UncheckedIOException("table unavailable: " + path, e);
        }
        return rows;
    }

    List<String> distinct(String column) {
        LinkedHashSet<String> values = new LinkedHashSet<>();
        for (Map<String, String> row : select(r -> true)) values.add(row.get(column));
        return new ArrayList<>(values);
    }
}
