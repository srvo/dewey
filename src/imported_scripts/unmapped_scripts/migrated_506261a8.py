dofrom celadon import View, Text
from celadon.styles import Style, Color
from rich.panel import Panel
from rich.layout import Layout

class NavigationView(View):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.current_view = 'main'  # main, company_list, company_detail
        self.selected_company = None
        self.help_visible = False
        
    def handle_input(self, key):
        if key == '?':
            self.help_visible = not self.help_visible
            return True
            
        if self.current_view == 'main':
            if key == 'l':  # List view
                self.current_view = 'company_list'
                return True
            elif key == 'r':  # Review queue
                self.app.focus_review_queue()
                return True
                
        elif self.current_view == 'company_list':
            if key == 'esc':
                self.current_view = 'main'
                return True
            elif key == 'enter' and self.selected_company:
                self.current_view = 'company_detail'
                return True
            elif key in ['j', 'k']:  # vim-style navigation
                self.app.navigate_companies(up=(key == 'k'))
                return True
                
        elif self.current_view == 'company_detail':
            if key == 'esc':
                self.current_view = 'company_list'
                return True
            elif key == 'n':  # Add note
                self.app.add_note()
                return True
            elif key == 't':  # Update tick
                self.app.update_tick()
                return True
                
        return False
        
    def render(self):
        if not self.help_visible:
            return None
            
        help_text = {
            'main': """
            Global Commands:
            ? - Toggle help
            l - Company list
            r - Review queue
            q - Quit
            """,
            'company_list': """
            List Navigation:
            j/k - Move up/down
            enter - View details
            esc - Back to main
            s - Sort by...
            f - Filter...
            """,
            'company_detail': """
            Company View:
            n - Add note
            t - Update tick
            h - View history
            esc - Back to list
            """
        }
        
        return Panel(
            help_text.get(self.current_view, ""),
            title="Keyboard Commands",
            style="bright_black"
        )

class CompanySelector:
    def __init__(self, universe_df):
        self.universe_df = universe_df
        self.current_index = 0
        self.filter_criteria = None
        self.sort_by = 'Tick'
        self.sort_ascending = False
        
    def get_filtered_companies(self):
        df = self.universe_df
        if self.filter_criteria:
            # Apply filters
            pass
        return df.sort_values(self.sort_by, ascending=self.sort_ascending)
        
    def move_selection(self, up=False):
        companies = self.get_filtered_companies()
        if up:
            self.current_index = max(0, self.current_index - 1)
        else:
            self.current_index = min(len(companies) - 1, self.current_index + 1)
            
    def get_selected_company(self):
        companies = self.get_filtered_companies()
        if not companies.empty and self.current_index < len(companies):
            return companies.iloc[self.current_index]
        return None
        
    def set_filter(self, criteria):
        self.filter_criteria = criteria
        self.current_index = 0
        
    def set_sort(self, column, ascending=False):
        self.sort_by = column
        self.sort_ascending = ascending
        self.current_index = 0
