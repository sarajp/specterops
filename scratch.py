char_row = []
current_char_code = ord('A')
for i in range(0, 23):
    char_row.append(chr(current_char_code))
    current_char_code += 1
char_grid = [char_row]*32

num_grid = []
for i in range(1, 33):
    num_row = [str(i)]*23
    num_grid.append(num_row)

board_grid = [[char_grid[i][j] + num_grid[i][j] for j in range(23)] for i in range(32)]

for b in board_grid:
    print(b)

content = ''
start_x = 15
start_y = 17
for i, row in enumerate(board_grid):
    for j, cell in enumerate(row):
        line = f'<rect id="{cell}" x="{(20*j)+start_x}" y="{(20*i)+start_y}" width="20" height="20" fill="none" stroke="red" pointer-events="all" cursor="pointer" />\n'
        print(line)
        1/0




content='''
        <rect id="N1" x="344" y="17" width="20" height="20" fill="none" stroke="red" pointer-events="all" cursor="pointer" />
        <rect id="K17" x="268" y="415" width="20" height="20" fill="none" stroke="red" pointer-events="all" cursor="pointer" />
        '''