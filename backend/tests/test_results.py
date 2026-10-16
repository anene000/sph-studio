"""Phase C: frame CSV scalar extraction (pressure / speed) for the colormap viewer."""
from app import results


def test_read_csv_rows_extracts_pressure_and_speed(tmp_path):
    csv = tmp_path / "fluid_0_000000.csv"
    csv.write_text(
        "# simTime 0.0\n"
        "x,y,z,vx,vy,vz,density,pressure\n"
        "0.1,0.2,0.3,1,0,0,1000,10\n"
        "0.4,0.5,0.6,0,3,4,1000,25\n",
        encoding="utf-8",
    )
    pos, pressure, speed = results._read_csv_rows(csv)
    assert pos == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert pressure == [10.0, 25.0]
    # speed = |v|: first row 1, second row sqrt(0+9+16)=5
    assert speed[0] == 1.0 and abs(speed[1] - 5.0) < 1e-9


def test_read_csv_rows_positions_only_when_no_scalar_columns(tmp_path):
    csv = tmp_path / "obj.csv"
    csv.write_text("x,y,z\n0,0,0\n1,1,1\n", encoding="utf-8")
    pos, pressure, speed = results._read_csv_rows(csv)
    assert pos == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    assert pressure == [] and speed == []
