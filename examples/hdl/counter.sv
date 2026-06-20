module counter #(
    parameter int WIDTH = 8
) (
    input  logic             clk,
    input  logic             reset_n,
    input  logic             enable,
    output logic [WIDTH-1:0] count
);

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            count <= '0;
        end else if (enable) begin
            count <= count + 1'b1;
        end
    end

endmodule
