"""
RiskGuard — Base App
Base App. This still needs some work, but this is basically what the base app will look like.
Run on desktop:
  pip install kivy
  python main.py
"""

#kivy important import stuff
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.core.window import Window
from kivy.animation import Animation

Window.size = (360, 700)

BG0      = (0.06, 0.06, 0.07, 1)
BG1      = (0.10, 0.10, 0.12, 1)
BORDER   = (0.18, 0.18, 0.21, 1)
ACCENT   = (0.38, 0.78, 0.60, 1)
TEXT_PRI = (0.91, 0.91, 0.93, 1)
TEXT_SEC = (0.50, 0.50, 0.55, 1)
TEXT_DIM = (0.28, 0.28, 0.32, 1)
C_RED    = (0.93, 0.38, 0.28, 1)
C_AMBER  = (0.90, 0.68, 0.22, 1)
#color garbage. Wanted to make this as dark as possible.

def add_bg(widget, color, radius=0):
    #this is the helper function i made to add the background color to every window//label.
    with widget.canvas.before: #before, because i want the color to be in the background
        Color(*color)
        if radius:
            r = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        else:
            r = Rectangle(pos=widget.pos, size=widget.size)
    def _upd(*_): #this is my helper for resizing the window
        r.pos  = widget.pos
        r.size = widget.size
    widget.bind(pos=_upd, size=_upd)


class Divider(Widget):
    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(1), **kwargs)
        with self.canvas: #this is the function that i use to draw a horizontal line on the screen, to divide preferences.
            Color(*BORDER)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._r, 'pos', self.pos),
                  size=lambda *_: setattr(self._r, 'size', self.size)) #updates the position of this line dynamically



class HeaderBar(BoxLayout):
    def __init__(self, title='RISKGUARD', show_back=False, on_back=None, **kwargs):
        super().__init__(orientation='horizontal',
                         size_hint_y=None, height=dp(56),
                         padding=[dp(16), 0], spacing=dp(10), **kwargs)
        add_bg(self, BG1) #adding background, as always

        if show_back:
            btn = Button(text='<-', font_size=dp(20), color=ACCENT,
                         size_hint=(None, 1), width=dp(36),
                         background_color=(0, 0, 0, 0),
                         background_normal='')
            if on_back:
                btn.bind(on_press=on_back)
            self.add_widget(btn)

        dot = Label(text='●', font_size=dp(9), color=ACCENT,
                    size_hint=(None, 1), width=dp(14))
        title_lbl = Label(text=title, font_size=dp(13), bold=True,
                          color=TEXT_PRI, size_hint_x=1, halign='left')
        self._status_lbl = Label(text='ON', font_size=dp(9), #want this to indicate enabling or disabling RiskAnalyser
                                 color=ACCENT, size_hint=(None, 1),
                                 width=dp(60), halign='right')
        for w in (dot, title_lbl, self._status_lbl):
            self.add_widget(w)

    def set_status(self, text, color=None):
        #i use this function to dynamically update text. (This will dynamically update my RiskAnalyser status later)
        self._status_lbl.text  = text
        self._status_lbl.color = color or ACCENT



class StatCard(BoxLayout):
    def __init__(self, key, value='—', val_color=None, **kwargs):
        super().__init__(orientation='vertical',
                         size_hint_y=None, height=dp(68),
                         padding=dp(10), spacing=dp(2), **kwargs)
        add_bg(self, BG1, radius=dp(8)) #background, same as everything else, orientation is also same as everything else.
        self.val_lbl = Label(text=str(value), font_size=dp(20),
                             bold=True, color=val_color or TEXT_PRI)
        self.key_lbl = Label(text=key, font_size=dp(9), color=TEXT_DIM) #this is going to make the labels for my numbers.
        self.add_widget(self.val_lbl)
        self.add_widget(self.key_lbl) #adds the widget.

    def update(self, value, color=None): #dynamically lets me change the value on the screen. Will fix this later.
        self.val_lbl.text = str(value)
        if color:
            self.val_lbl.color = color

class EmptyState(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=dp(10),
                         padding=[dp(40), dp(60), dp(40), 0], **kwargs)
        icon = Label(text='◎', font_size=dp(44), color=TEXT_DIM,
                     size_hint_y=None, height=dp(60)) #same as everything else.
        msg  = Label(
            text='No messages yet.\nGrant Notification Access to begin.',
            font_size=dp(12), color=TEXT_DIM,
            halign='center', valign='top', #i actually have no idea why this isnt showing up. Bug, will fix later.
            size_hint_y=None, height=dp(60),
        )
        msg.bind(size=lambda i, v: setattr(i, 'text_size', v))
        for w in (icon, msg):
            self.add_widget(w)
        self.opacity = 0
        Animation(opacity=1, duration=0.6).start(self)



class PrefToggle(BoxLayout):
    def __init__(self, title, subtitle, key, default=True, **kwargs):
        super().__init__(orientation='horizontal',
                         size_hint_y=None, height=dp(62),
                         padding=[dp(18), dp(8)], spacing=dp(12), **kwargs)
        col = BoxLayout(orientation='vertical', spacing=dp(3)) #same things, making labels, dum de dum dum
        t = Label(text=title, font_size=dp(13), color=TEXT_PRI,
                  halign='left', valign='middle')
        s = Label(text=subtitle, font_size=dp(10), color=TEXT_SEC,
                  halign='left', valign='middle') #these are the base labels for my toggle buttons!
        for lbl in (t, s):
            lbl.bind(size=lambda i, v: setattr(i, 'text_size', v))
            col.add_widget(lbl)
        sw = Switch(active=default, size_hint=(None, 1), width=dp(60)) #switch is the actual toggle button
        sw.bind(active=lambda i, v, k=key: print(f'[Pref] {k} = {v}'))
        self.add_widget(col)
        self.add_widget(sw)


class PrefSection(BoxLayout):
    def __init__(self, heading, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None,
                         spacing=0, **kwargs)
        self.bind(minimum_height=self.setter('height')) #using this for dynamic sizing
        hdr = Label(text=heading.upper(), font_size=dp(9), color=TEXT_DIM,
                    bold=True, size_hint_y=None, height=dp(34), halign='left')
        hdr.bind(size=lambda i, v: setattr(i, 'text_size', (v[0] - dp(18), v[1])))
        self.add_widget(hdr)

    def add_row(self, row):
        self.add_widget(Divider()) #adds a dynamically sized divider after each button.
        self.add_widget(row)



class NavTab(BoxLayout):
    active = BooleanProperty(False)

    def __init__(self, label, **kwargs):
        super().__init__(orientation='vertical', spacing=0,
                         padding=[0, dp(4)], **kwargs) #again, vertical layout, no spacing
        self._cb = None

        self._bar = Widget(size_hint_y=None, height=dp(2))

        self._icon_lbl = Label(font_size=dp(16), color=TEXT_DIM,
                               size_hint_y=None, height=dp(22))
        self._text_lbl = Label(text=label, font_size=dp(9),  color=TEXT_DIM,
                               size_hint_y=None, height=dp(14))

        self.add_widget(self._bar)
        self.add_widget(self._icon_lbl)
        self.add_widget(self._text_lbl) #adding my widgets, as usual

        self.bind(active=self._refresh)
        self._bar.bind(pos=self._draw_bar, size=self._draw_bar)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self._cb:
            self._cb()
            return True
        return super().on_touch_down(touch)

    def set_callback(self, cb):
        self._cb = cb #for tab switching.

    def _refresh(self, *_):
        #this is my code for HIHGLIGHTING the current tab
        col = ACCENT if self.active else TEXT_DIM
        self._icon_lbl.color = col
        self._text_lbl.color = col
        self._draw_bar()

    def _draw_bar(self, *_):
        self._bar.canvas.clear()
        if self.active:
            with self._bar.canvas:
                Color(*ACCENT)
                RoundedRectangle(
                    pos=(self._bar.x + self._bar.width / 2 - dp(16), self._bar.y),
                    size=(dp(32), dp(2)),
                    radius=[dp(1)],
                ) #i wanted to draw a cute little line, so i did.



class BottomNav(BoxLayout):
    """This class is where i put the animation for the bottom bar."""
    def __init__(self, on_nav, **kwargs):
        super().__init__(orientation='horizontal',
                         size_hint_y=None, height=dp(54), **kwargs) #Sets the layout of the label to be horizontal.
        add_bg(self, BG1) #same color background as the other stuff.

        self._tabs = {}
        for key, label in [('home', 'Feed'), ('prefs', 'Settings')]: #here are the windows that i defined earlier! I'm basically mapping these labels to the windows.
            t = NavTab(label, size_hint_x=1)
            t.set_callback(lambda k=key: on_nav(k)) #this is how i get the key, so i know which tab (and therefore which widget) is being used.
            self._tabs[key] = t
            self.add_widget(t)

        self.set_active('home') #this is the default active tab.

    def set_active(self, key):
        for k, t in self._tabs.items():
            t.active = (k == key) #this loop will turn on the selected and calculated label, and turn off the others.

    def _upd(self, *_):
        self._top.pos  = self.pos
        self._top.size = (self.width, dp(1))



class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical')
        add_bg(root, BG0)  #Sets the orientation and background color for this specific screen.

        self.header = HeaderBar()

        stats = BoxLayout(size_hint_y=None, height=dp(84),
                          spacing=dp(6), padding=[dp(10), dp(8)]) #Makes the container for the top Risk Viewer part
        add_bg(stats, BG0) #Sets the background for the layout, same as everything else.
        self.s_total = StatCard('TOTAL',    '0', TEXT_PRI) #change the value of this number when scams are detected.
        self.s_high  = StatCard('HIGH+',    '0', C_RED)
        self.s_avg   = StatCard('AVG RISK', '—', TEXT_SEC)
        self.s_scam  = StatCard('SCAM',     '0', C_RED)

        for c in (self.s_total, self.s_high, self.s_avg, self.s_scam):
            stats.add_widget(c) #Adds all the created widgets with the labels and texts.

        scroll_header = BoxLayout(size_hint_y=None, height=dp(30),
                             padding=[dp(14), 0])


        self.scroll = ScrollView(do_scroll_x=False)
        self._empty = EmptyState()

        for w in (self.header, stats, scroll_header, self.scroll):
            root.add_widget(w)

        self.add_widget(root) #adds the scrolling widget.

class PreferencesScreen(Screen):
    """ This class is the second preferences screen, and consists of toggleable buttons and a few more labels."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical')
        add_bg(root, BG0) #same thing as all the others, this screen is a vertical box layout with my pretty dark background.

        header = HeaderBar(title='PREFERENCES', show_back=True,
                           on_back=self._back) #Top header.

        scroll = ScrollView(do_scroll_x=False) #need a scrollview for this screen aswell.
        layout = BoxLayout(orientation='vertical', size_hint_y=None,
                           spacing=dp(14), padding=[0, dp(10), 0, dp(30)])
        layout.bind(minimum_height=layout.setter('height'))
        #these are all of the buttons!!
        s1 = PrefSection('Detection')
        s1.add_row(PrefToggle('Scam detection',
                              'Flag phishing',
                              key='detect_scam'))
        s2 = PrefSection('Alerts')
        s2.add_row(PrefToggle('High-risk notifications',
                              'Vibrate and notify on score >= 80',
                              key='alert_high'))
        s2.add_row(PrefToggle('Sound alerts',
                              'Play a tone for critical messages',
                              key='alert_sound', default=False))

        s3 = PrefSection('Performance')
        s3.add_row(PrefToggle('Battery saver',
                              'Reduce or disable background scanning frequency',
                              key='battery_saver', default=False))
        s3.add_row(PrefToggle('Run on startup',
                              'Start monitoring when device boots',
                              key='run_on_boot'))


        for s in (s1, s2, s3):
            layout.add_widget(s) #adds all the funny little buttons to the screen.

        scroll.add_widget(layout)
        for w in (header, scroll):
            root.add_widget(w) #adds the header and scroll to the root widget
        self.add_widget(root) #adds the root widget to base

    def _back(self, *_):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home' #This is how we transition back to home! And we animate it sliding back.



class RootLayout(BoxLayout):
    """ This is essentially the pure barebones layout. The children here are added vertically, because the orientation is
    vertical.
    """
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs) #this class inherits from boxlayout and adds to it.
        add_bg(self, BG0) #Sets the background to the base layout.
        #2 screens are made here. Kivy actually runs both of these at the same time, but it hides one.
        self.sm = ScreenManager()
        self.home  = HomeScreen(name='home')
        self.prefs = PreferencesScreen(name='prefs')
        self.sm.add_widget(self.home) #adding widgets to the home screen
        self.sm.add_widget(self.prefs) #adding widgets to the preferences tab

        self.nav = BottomNav(on_nav=self._nav) #tells me which navigation bar is being used, and switches to that.
        self.add_widget(self.sm)
        self.add_widget(self.nav) #adds nav and screenmanager as widgets.

    def _nav(self, key):
        self.nav.set_active(key) #highlight the current tab
        self.sm.transition = SlideTransition(
            direction='left' if key != 'home' else 'right')
        self.sm.current = key #sets the current screen to the tab that was found.

class RunApp(App):
    title = 'RiskGuard'

    def build(self):
        Window.clearcolor = BG0
        return RootLayout()

def main():
    """Runs the app instance. This essentially hands over complete flow control to kivy, and it manages all GUI elements from there on out."""
    RunApp().run()
main()
