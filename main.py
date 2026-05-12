"""
NORUSH — Final App!
This is the final norush app. This is where metrics are updated, messages are passed into here from android_sms.py, and send to riskanalyzer.
"""

#IMPORTS
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
from kivy.properties import BooleanProperty
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock

from android_sms import create_receiver_for_app

from storage import (
    save_decision,
    load_state,
    save_state,
    load_decisions,
    save_attention_summary,
    save_reward_summary,
)
from risk_analyzer import analyze_in_background, analyze_remote

import random
import time
import os


BG0 = (0.06, 0.06, 0.07, 1)
BG1 = (0.10, 0.10, 0.12, 1)
BORDER = (0.18, 0.18, 0.21, 1)
ACCENT = (0.38, 0.78, 0.60, 1)
TEXT_PRI = (0.91, 0.91, 0.93, 1)
TEXT_SEC = (0.50, 0.50, 0.55, 1)
TEXT_DIM = (0.28, 0.28, 0.32, 1)
C_RED   = (0.93, 0.38, 0.28, 1)
C_AMBER = (0.90, 0.68, 0.22, 1)
C_BLUE  = (0.25, 0.55, 0.85, 1)


def add_bg(widget, color, radius=0):
    """Paint a solid (optionally rounded) background rectangle on *widget*.
    """
    with widget.canvas.before:
        Color(*color)
        if radius:
            r = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        else:
            r = Rectangle(pos=widget.pos, size=widget.size)

    def _upd(*_):
        r.pos = widget.pos
        r.size = widget.size

    widget.bind(pos=_upd, size=_upd)


class Divider(Widget):
    """A 1 dp horizontal line used to separate rows inside PrefSection."""
    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(1), **kwargs)
        with self.canvas:
            Color(*BORDER)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(
            pos=lambda *_: setattr(self._r, "pos", self.pos),
            size=lambda *_: setattr(self._r, "size", self.size),
        )


class HeaderBar(BoxLayout):
    """Top navigation bar with optional back button, logo dot, title, and status text."""
    def __init__(self, title="NoRush", show_back=False, on_back=None, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(16), 0],
            spacing=dp(10),
            **kwargs,
        )
        add_bg(self, BG1)

        # Optional back arrow rendered as a plain text button.
        if show_back:
            btn = Button(
                text="<-",
                font_size=dp(20),
                color=ACCENT,
                size_hint=(None, 1),
                width=dp(36),
                background_color=(0, 0, 0, 0),
                background_normal="",
            )
            if on_back:
                btn.bind(on_press=on_back)
            self.add_widget(btn)

        dot = Label(
            text="●",
            font_size=dp(9),
            color=ACCENT,
            size_hint=(None, 1),
            width=dp(14),
        )
        title_lbl = Label(
            text=title,
            font_size=dp(13),
            bold=True,
            color=TEXT_PRI,
            size_hint_x=1,
            halign="left",
        )
        # Status label — updated at runtime by set_status() to show the
        # current scanning state ("ON", "SCANNING", risk level, etc.).
        self._status_lbl = Label(
            text="ON",
            font_size=dp(9),
            color=ACCENT,
            size_hint=(None, 1),
            width=dp(72),
            halign="right",
        )
        for w in (dot, title_lbl, self._status_lbl):
            self.add_widget(w)

    def set_status(self, text, color=None):
        """Update the right-aligned status indicator text and colour."""
        self._status_lbl.text = text
        self._status_lbl.color = color or ACCENT


class StatCard(BoxLayout):
    """A compact card showing a large metric value above a small key label."""
    def __init__(self, key, value="—", val_color=None, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(68),
            padding=dp(10),
            spacing=dp(2),
            **kwargs,
        )
        add_bg(self, BG1, radius=dp(8))
        self.val_lbl = Label(
            text=str(value),
            font_size=dp(20),
            bold=True,
            color=val_color or TEXT_PRI,
        )
        self.key_lbl = Label(text=key, font_size=dp(9), color=TEXT_DIM)
        self.add_widget(self.val_lbl)
        self.add_widget(self.key_lbl)

    def update(self, value, color=None):
        """Refresh the displayed value; optionally change its colour."""
        self.val_lbl.text = str(value)
        if color:
            self.val_lbl.color = color


class EmptyState(BoxLayout):
    """Placeholder widget shown in the feed when no messages have been analyzed yet.

    Fades in via an opacity animation to avoid a jarring instant appearance.
    """
    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(40), dp(40), dp(40), 0],
            size_hint_y=None,
            height=dp(130),
            **kwargs,
        )
        icon = Label(
            text="◎",
            font_size=dp(44),
            color=TEXT_DIM,
            size_hint_y=None,
            height=dp(60),
        )
        msg = Label(
            text="No analyzed messages yet.\nUse the demo buttons below.",
            font_size=dp(12),
            color=TEXT_DIM,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(60),
        )
        msg.bind(size=lambda i, v: setattr(i, "text_size", v))
        for w in (icon, msg):
            self.add_widget(w)
        # Start invisible and animate to full opacity over 600 ms.
        self.opacity = 0
        Animation(opacity=1, duration=0.6).start(self)


class PrefToggle(BoxLayout):
    """A labelled on/off toggle row for the preferences screen.
    """
    def __init__(self, title, subtitle, key, default=True, on_change=None, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(62),
            padding=[dp(18), dp(8)],
            spacing=dp(12),
            **kwargs,
        )
        col = BoxLayout(orientation="vertical", spacing=dp(3))
        t = Label(
            text=title,
            font_size=dp(13),
            color=TEXT_PRI,
            halign="left",
            valign="middle",
        )
        s = Label(
            text=subtitle,
            font_size=dp(10),
            color=TEXT_SEC,
            halign="left",
            valign="middle",
        )
        for lbl in (t, s):
            lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
            col.add_widget(lbl)

        # Load persisted value for battery_saver, fall back to default
        if key == "battery_saver":
            state = load_state()
            default = state.get("battery_saver", default)

        sw = Switch(active=default, size_hint=(None, 1), width=dp(60))

        def _on_active(instance, value):
            print(f"[Pref] {key} = {value}")
            if on_change:
                on_change(value)

        sw.bind(active=_on_active)

        self.add_widget(col)
        self.add_widget(sw)


class PrefSection(BoxLayout):
    """A vertically stacked group of preference rows under a heading label."""
    def __init__(self, heading, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=0, **kwargs)
        # height tracks content so the parent ScrollView can size correctly.
        self.bind(minimum_height=self.setter("height"))
        hdr = Label(
            text=heading.upper(),
            font_size=dp(9),
            color=TEXT_DIM,
            bold=True,
            size_hint_y=None,
            height=dp(34),
            halign="left",
        )
        hdr.bind(size=lambda i, v: setattr(i, "text_size", (v[0] - dp(18), v[1])))
        self.add_widget(hdr)

    def add_row(self, row):
        """Append a Divider then *row* to the section."""
        self.add_widget(Divider())
        self.add_widget(row)


class NavTab(BoxLayout):
    active = BooleanProperty(False)

    def __init__(self, label, **kwargs):
        super().__init__(orientation="vertical", spacing=0, padding=[0, dp(4)], **kwargs)
        self._cb = None
        self._bar = Widget(size_hint_y=None, height=dp(2))
        self._icon_lbl = Label(font_size=dp(16), color=TEXT_DIM, size_hint_y=None, height=dp(22))
        self._text_lbl = Label(text=label, font_size=dp(9), color=TEXT_DIM, size_hint_y=None, height=dp(14))
        self.add_widget(self._bar)
        self.add_widget(self._icon_lbl)
        self.add_widget(self._text_lbl)
        self.bind(active=self._refresh)
        self._bar.bind(pos=self._draw_bar, size=self._draw_bar)

    def on_touch_down(self, touch):
        """Fire the stored callback when the user taps anywhere on this tab."""
        if self.collide_point(*touch.pos) and self._cb:
            self._cb()
            return True
        return super().on_touch_down(touch)

    def set_callback(self, cb):
        """Register the callable that is invoked on tap."""
        self._cb = cb

    def _refresh(self, *_):
        """Re-colour the icon and text to reflect the current active state."""
        col = ACCENT if self.active else TEXT_DIM
        self._icon_lbl.color = col
        self._text_lbl.color = col
        self._draw_bar()

    def _draw_bar(self, *_):
        """Draw (or clear) the active-indicator bar above the tab icon."""
        self._bar.canvas.clear()
        if self.active:
            with self._bar.canvas:
                Color(*ACCENT)
                RoundedRectangle(
                    pos=(self._bar.x + self._bar.width / 2 - dp(16), self._bar.y),
                    size=(dp(32), dp(2)),
                    radius=[dp(1)],
                )


class BottomNav(BoxLayout):
    """Persistent two-tab navigation bar (Feed / Settings) at the bottom of the screen."""
    def __init__(self, on_nav, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(54), **kwargs)
        add_bg(self, BG1)
        self._tabs = {}
        for key, label in [("home", "Feed"), ("prefs", "Settings")]:
            t = NavTab(label, size_hint_x=1)
            t.set_callback(lambda k=key: on_nav(k))
            self._tabs[key] = t
            self.add_widget(t)
        self.set_active("home")

    def set_active(self, key):
        """Mark the tab matching *key* as active; deactivate all others."""
        for k, t in self._tabs.items():
            t.active = (k == key)


class SMSCard(BoxLayout):
    def __init__(self, sms_text, result, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            height=dp(124),
            padding=dp(12),
            spacing=dp(6),
            **kwargs,
        )
        add_bg(self, BG1, radius=dp(8))

        score_pct = int(round(result["behavioral_risk_score"] * 100))
        level = result["risk_level"]
        tactic = result["dominant_tactic"]

        level_color = {
            "LOW": ACCENT,
            "MEDIUM": C_AMBER,
            "HIGH": C_RED,
            "CRITICAL": C_RED,
        }.get(level, TEXT_SEC)

        top = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(8))
        top.add_widget(
            Label(
                text=level,
                font_size=dp(10),
                bold=True,
                color=level_color,
                size_hint_x=None,
                width=dp(80),
                halign="left",
            )
        )
        top.add_widget(
            Label(
                text=f"Score: {score_pct}",
                font_size=dp(10),
                color=TEXT_SEC,
                halign="left",
            )
        )

        preview = Label(
            text=sms_text[:85] + ("..." if len(sms_text) > 85 else ""),
            font_size=dp(11),
            color=TEXT_PRI,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(38),
        )
        preview.bind(size=lambda i, v: setattr(i, "text_size", v))

        bottom = Label(
            text=f"Tactic: {tactic}",
            font_size=dp(9),
            color=TEXT_DIM,
            halign="left",
            size_hint_y=None,
            height=dp(18),
        )
        bottom.bind(size=lambda i, v: setattr(i, "text_size", v))

        for w in (top, preview, bottom):
            self.add_widget(w)


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical")
        add_bg(root, BG0)

        self.header = HeaderBar()

        stats = BoxLayout(size_hint_y=None, height=dp(84), spacing=dp(6), padding=[dp(10), dp(8)])
        add_bg(stats, BG0)
        self.s_total = StatCard("TOTAL", "0", TEXT_PRI)
        self.s_high = StatCard("HIGH+", "0", C_RED)
        self.s_avg = StatCard("AVG RISK", "—", TEXT_SEC)
        self.s_reports = StatCard("REPORTS", "0", C_RED)
        self.s_behavior = StatCard("BEHAVIOR", "—", C_AMBER)
        for c in (self.s_total, self.s_high, self.s_avg, self.s_reports, self.s_behavior):
            stats.add_widget(c)

        # Task buttons sit ABOVE the scroll — always visible
        self.attention_btn = Button(
            text="Open Attention Task",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.80, 0.45, 0.05, 1),  # amber-orange
        )
        self.reward_btn = Button(
            text="Open Reward Task",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.70, 0.55, 0.05, 1),  # amber-yellow
        )
        self.attention_btn.bind(on_press=self._open_attention)
        self.reward_btn.bind(on_press=self._open_reward)

        task_btn_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(8),
            padding=[dp(8), dp(4)],
        )
        add_bg(task_btn_bar, BG1)
        task_btn_bar.add_widget(self.attention_btn)
        task_btn_bar.add_widget(self.reward_btn)

        self.scroll = ScrollView(do_scroll_x=False)
        self._feed = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(8), dp(8)],
        )
        self._feed.bind(minimum_height=self._feed.setter("height"))
        self._empty = EmptyState()
        self._feed.add_widget(self._empty)

        self.scroll.add_widget(self._feed)

        root.add_widget(self.header)
        root.add_widget(stats)
        root.add_widget(task_btn_bar)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def receive_sms(self, sms_text: str):
        """Entry point called by AndroidSMSReceiver whenever a new SMS arrives.

        Sets the header to "SCANNING" immediately for visual feedback, then
        dispatches analysis to a background thread to keep the UI responsive.
        Routes to remote server or local analysis based on battery_saver setting.
        """
        self.header.set_status("SCANNING", color=C_AMBER)
        state = load_state()

        def _done(result):
            # Always dispatch to the Kivy main thread — analysis runs in a
            # background thread and Kivy UI calls are not thread-safe.
            Clock.schedule_once(lambda dt: self.on_analysis_done(sms_text, result), 0)

        if state.get("battery_saver", False):
            # Battery saver ON: offload heavy analysis to the remote PC server.
            analyze_remote(sms_text, _done)
        else:
            # Battery saver OFF: run analysis on-device in a background thread.
            analyze_in_background(sms_text, _done)

    def on_analysis_done(self, sms_text: str, result: dict):
        """Called on the main thread once risk analysis completes.
        """
        score_pct = int(round(result["behavioral_risk_score"] * 100))
        level = result["risk_level"]
        dominant_tactic = result.get("dominant_tactic", "unknown")

        # Remove the empty-state placeholder on first real message.
        if self._empty in self._feed.children:
            self._feed.remove_widget(self._empty)

        self._feed.add_widget(SMSCard(sms_text, result))

        status_color = {
            "LOW": ACCENT,
            "MEDIUM": C_AMBER,
            "HIGH": C_RED,
            "CRITICAL": C_RED,
        }.get(level, ACCENT)
        self.header.set_status(level, color=status_color)

        if score_pct >= 50:
            # High / critical risk — show the friction intervention screen.
            screen = self.manager.get_screen("intervention")
            screen.load_message(sms_text, score_pct, dominant_tactic=dominant_tactic)
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "intervention"
        else:
            # Low-risk messages are never shown in the intervention screen,
            # so save them here directly — high-risk are saved on user action.
            save_decision("auto_cleared", sms_text, score_pct, 0, dominant_tactic=dominant_tactic)
            self.refresh_stats()

    def refresh_stats(self):
        """Recompute and redraw all five stat cards from persisted decision log."""
        decisions = load_decisions()
        state = load_state()

        total = len(decisions)
        high_count = sum(1 for d in decisions if d.get("risk_score", 0) >= 80)
        avg_risk = round(sum(d.get("risk_score", 0) for d in decisions) / total, 1) if total else "—"
        reports = sum(1 for d in decisions if d.get("action") == "report")

        self.s_total.update(total)
        self.s_high.update(high_count, C_RED)
        self.s_avg.update(avg_risk, TEXT_SEC if avg_risk == "—" else C_AMBER)
        self.s_reports.update(reports, C_RED)

        behavior_score = state.get("behavioral_intervention_score")

        if behavior_score is None:
            behavior_score = state.get("attention_score")

        behavior_text = "—" if behavior_score is None else f"{behavior_score}/100"
        self.s_behavior.update(behavior_text, C_AMBER)

        level = state.get("impulsivity_level", "unknown").upper()
        self.header.set_status(level, C_AMBER if level != "UNKNOWN" else ACCENT)

    def on_pre_enter(self, *args):
        """Rebuild the feed from the persistent decision log each time the screen is entered.
        """
        decisions = load_decisions()
        self.refresh_stats()
        self._feed.clear_widgets()

        if not decisions:
            # Nothing logged yet — show the empty state placeholder.
            self._empty = EmptyState()
            self._feed.add_widget(self._empty)
            return

        for entry in decisions:
            # Re-derive risk level from the stored score percentage so the
            # feed card colours match the current thresholds.
            score = entry.get("risk_score", 0) / 100
            if score < 0.40: level = "LOW"
            elif score < 0.65: level = "MEDIUM"
            elif score < 0.85: level = "HIGH"
            else: level = "CRITICAL"

            result = {
                "behavioral_risk_score": score,
                "risk_level": level,
                "dominant_tactic": entry.get("dominant_tactic", "unknown"),
            }
            self._feed.add_widget(SMSCard(entry.get("message_text", ""), result))

    def _open_attention(self, *_):
        """Navigate to the attention (go/no-go) task screen."""
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "attention"

    def _open_reward(self, *_):
        """Navigate to the reward-sensitivity task screen."""
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "reward"


class PreferencesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical")
        add_bg(root, BG0)

        header = HeaderBar(title="PREFERENCES", show_back=True, on_back=self._back)
        scroll = ScrollView(do_scroll_x=False)
        layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(14),
            padding=[0, dp(10), 0, dp(30)],
        )
        layout.bind(minimum_height=layout.setter("height"))

        s1 = PrefSection("Performance")
        s1.add_row(
            PrefToggle(
                "Battery saver",
                "Offload analysis to your remote PC",
                key="battery_saver",
                default=False,
                on_change=self._on_battery_saver_changed,
            )
        )

        s2 = PrefSection("Simulate")

        sim_risky_btn = Button(
            text="Simulate Risky Message",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.85, 0.38, 0.05, 1),
        )
        sim_safe_btn = Button(
            text="Simulate Safe Message",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.75, 0.60, 0.05, 1),
        )

        def _sim_risky(*_):
            home = self.manager.get_screen("home")
            home.receive_sms(
                "URGENT: Your bank account has been suspended. Verify now at "
                "http://secure-bank-login.000webhostapp.com"
            )
            self.manager.transition = SlideTransition(direction="right")
            self.manager.current = "home"

        def _sim_safe(*_):
            home = self.manager.get_screen("home")
            home.receive_sms("Hey, are you still coming to dinner tonight? Let me know by 6.")
            self.manager.transition = SlideTransition(direction="right")
            self.manager.current = "home"

        sim_risky_btn.bind(on_press=_sim_risky)
        sim_safe_btn.bind(on_press=_sim_safe)
        s2.add_row(sim_risky_btn)
        s2.add_row(sim_safe_btn)

        for s in (s1, s2):
            layout.add_widget(s)

        scroll.add_widget(layout)
        root.add_widget(header)
        root.add_widget(scroll)
        self.add_widget(root)

    def _on_battery_saver_changed(self, value):
        """Persist the new battery_saver toggle state immediately on change."""
        state = load_state()
        state["battery_saver"] = value
        save_state(state)

    def _back(self, *_):
        """Navigate back to the home/feed screen."""
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"


class QuestionRow(BoxLayout):
    """A binary Yes / No question widget used on the InterventionScreen.
    """
    def __init__(self, question_text, on_answer=None, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(88), spacing=dp(8), **kwargs)
        self.on_answer = on_answer

        self.q_lbl = Label(
            text=question_text,
            color=TEXT_PRI,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(30),
        )
        self.q_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.yes_btn = Button(
            text="Yes",
            background_normal="",
            background_color=(0.15, 0.35, 0.15, 1),
        )
        self.no_btn = Button(
            text="No",
            background_normal="",
            background_color=(0.35, 0.15, 0.15, 1),
        )
        self.yes_btn.bind(on_press=lambda *_: self.set_answer("Yes"))
        self.no_btn.bind(on_press=lambda *_: self.set_answer("No"))
        btn_row.add_widget(self.yes_btn)
        btn_row.add_widget(self.no_btn)

        self.add_widget(self.q_lbl)
        self.add_widget(btn_row)

    def set_answer(self, answer):
        """Highlight the chosen button, dim the other, and notify the listener."""
        if answer == "Yes":
            self.yes_btn.background_color = (0.25, 0.55, 0.25, 1)  # brighter green
            self.no_btn.background_color = (0.35, 0.15, 0.15, 1)   # dim red
        else:
            self.no_btn.background_color = (0.55, 0.25, 0.25, 1)   # brighter red
            self.yes_btn.background_color = (0.15, 0.35, 0.15, 1)  # dim green

        if self.on_answer:
            self.on_answer(answer)


class InterventionScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.seconds_left = 5
        self.current_message = ""
        self.current_risk_score = 0
        self.current_dominant_tactic = "unknown"
        self.current_delay = 5
        self.q1_answer = None
        self.q2_answer = None

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        add_bg(root, BG0)

        header = HeaderBar(title="INTERVENTION", show_back=True, on_back=self._back)
        self.title_lbl = Label(
            text="High-Risk Message Detected",
            font_size=dp(18),
            bold=True,
            color=C_RED,
            size_hint_y=None,
            height=dp(40),
        )
        self.msg_lbl = Label(text="", markup=False, color=TEXT_PRI, halign="left", valign="top")
        self.msg_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.risk_lbl = Label(
            text="Risk Score: 0",
            font_size=dp(14),
            color=C_AMBER,
            size_hint_y=None,
            height=dp(30),
        )
        self.q1_widget = QuestionRow("Were you expecting this message?", on_answer=self._set_q1_answer)
        self.q2_widget = QuestionRow("Does the sender look familiar?", on_answer=self._set_q2_answer)
        self.timer_lbl = Label(
            text="Please wait 5 seconds before proceeding.",
            color=TEXT_SEC,
            size_hint_y=None,
            height=dp(30),
        )
        self.profile_lbl = Label(
            text="User profile: unknown",
            color=TEXT_DIM,
            size_hint_y=None,
            height=dp(24),
        )
        self.breakdown_lbl = Label(
            text="Delay breakdown: —",
            color=TEXT_DIM,
            font_size=dp(10),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(42),
        )
        self.breakdown_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.proceed_btn = Button(
            text="Proceed in 5...",
            size_hint_y=None,
            height=dp(48),
            disabled=True,
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 1),
        )
        self.report_btn = Button(
            text="Report as Suspicious",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.5, 0.1, 0.1, 1),
        )
        self.proceed_btn.bind(on_press=self._proceed)
        self.report_btn.bind(on_press=self._report)

        for w in (
            header,
            self.title_lbl,
            self.msg_lbl,
            self.risk_lbl,
            self.profile_lbl,
            self.breakdown_lbl,
            self.q1_widget,
            self.q2_widget,
            self.timer_lbl,
            self.proceed_btn,
            self.report_btn,
        ):
            root.add_widget(w)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        """Reset and start the countdown timer each time this screen is shown."""
        self.seconds_left = self.current_delay
        self.proceed_btn.disabled = True
        self.proceed_btn.text = f"Proceed in {self.seconds_left}..."
        self.timer_lbl.text = f"Please wait {self.seconds_left} seconds before proceeding."
        Clock.unschedule(self._tick)
        Clock.schedule_interval(self._tick, 1)

    def _tick(self, dt):
        """Decrement the countdown; unlock the proceed button when it reaches zero."""
        self.seconds_left -= 1
        if self.seconds_left > 0:
            self.proceed_btn.text = f"Proceed in {self.seconds_left}..."
            self.timer_lbl.text = f"Please wait {self.seconds_left} seconds before proceeding."
        else:
            self.proceed_btn.disabled = False
            self.proceed_btn.text = "Proceed Anyway"
            self.timer_lbl.text = "You may proceed now."
            Clock.unschedule(self._tick)
        return True

    def _set_q1_answer(self, answer):
        """Store the user's response to question 1 ("Were you expecting this?")."""
        self.q1_answer = answer

    def _set_q2_answer(self, answer):
        """Store the user's response to question 2 ("Does the sender look familiar?")."""
        self.q2_answer = answer

    def get_delay_seconds(
        self,
        risk_score,
        risky_clicks=0,
        safe_reports=0,
        impulsivity_level="unknown",
        false_starts=0,
        attention_score=None,
    ):
        """Calculate the friction delay (in seconds) for an intervention.

        The delay is personalised: riskier messages and more impulsive users
        get longer pauses to promote deliberate decision-making.
        """
        if risk_score >= 85:
            delay = 7
        elif risk_score >= 70:
            delay = 5
        elif risk_score >= 50:
            delay = 3
        else:
            delay = 2

        # Users who have clicked through risky messages before get extra time.
        delay += min(risky_clicks, 3)

        # Impulsive users benefit from additional friction.
        if impulsivity_level == "high":
            delay += 2
        elif impulsivity_level == "moderate":
            delay += 1

        # High attention vulnerability score adds further delay.
        if attention_score is not None:
            if attention_score >= 75:
                delay += 3
            elif attention_score >= 50:
                delay += 2
            elif attention_score >= 30:
                delay += 1

        # False starts are a proxy for impulsive responding.
        delay += min(false_starts, 2)

        # Reward users who have correctly reported suspicious messages.
        delay -= min(safe_reports, 3)

        return max(2, min(delay, 12))

    def load_message(self, message_text, risk_score, dominant_tactic="unknown"):
        """Populate the intervention screen with data for the incoming high-risk message.

        Reads the current user state to compute a personalised delay, then
        updates all UI labels so they reflect this specific message.
        Called by HomeScreen.on_analysis_done() before navigating here.
        """
        state = load_state()
        risky_clicks = state.get("risky_clicks", 0)
        safe_reports = state.get("safe_reports", 0)
        impulsivity_level = state.get("impulsivity_level", "unknown")
        false_starts = state.get("reaction_false_starts", 0)
        attention_score = state.get("attention_score")
        false_reports = state.get("false_reports", 0)

        self.current_message = message_text
        self.current_risk_score = risk_score
        self.current_dominant_tactic = dominant_tactic
        self.current_delay = self.get_delay_seconds(
            risk_score,
            risky_clicks=risky_clicks,
            safe_reports=safe_reports,
            impulsivity_level=impulsivity_level,
            false_starts=false_starts,
            attention_score=attention_score,
        )

        # Reset per-message state so stale answers from a previous message
        # are never accidentally submitted with this one.
        self.seconds_left = self.current_delay
        self.q1_answer = None
        self.q2_answer = None
        self.msg_lbl.text = message_text
        self.risk_lbl.text = f"Risk Score: {risk_score}"
        self.profile_lbl.text = f"User profile: {impulsivity_level}"
        attention_text = "—" if attention_score is None else f"{attention_score}/100"
        self.breakdown_lbl.text = (
            f"Risk: {risk_score} | Attention: {attention_text}\n"
            f"Risky proceeds: {risky_clicks} | Reports: {safe_reports} | "
            f"False reports: {false_reports} | Delay: {self.current_delay}s"
        )

    def _proceed(self, *_):
        """User chose to proceed anyway. Log the decision and update state.

        If the message was high-risk (>= 70), increment risky_clicks so future
        delays for this user are longer (behavioural feedback loop).
        """
        save_decision(
            "proceed",
            self.current_message,
            self.current_risk_score,
            self.current_delay,
            self.q1_answer,
            self.q2_answer,
            dominant_tactic=self.current_dominant_tactic,
        )

        state = load_state()

        # Only penalise the user's profile for clearly high-risk decisions.
        if self.current_risk_score >= 70:
            state["risky_clicks"] = state.get("risky_clicks", 0) + 1

        save_state(state)

        home = self.manager.get_screen("home")
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"
        home.refresh_stats()

    def _report(self, *_):
        """User chose to report the message as suspicious.
        """
        save_decision(
            "report",
            self.current_message,
            self.current_risk_score,
            self.current_delay,
            self.q1_answer,
            self.q2_answer,
            dominant_tactic=self.current_dominant_tactic,
        )

        state = load_state()

        if self.current_risk_score >= 70:
            # Correctly identifying a dangerous message — reward with reduced future delay.
            state["safe_reports"] = state.get("safe_reports", 0) + 1
        elif self.current_risk_score < 50:
            # Flagging a safe message as suspicious — track false-positive rate.
            state["false_reports"] = state.get("false_reports", 0) + 1

        save_state(state)

        home = self.manager.get_screen("home")
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"
        home.refresh_stats()

    def _back(self, *_):
        # User backed out without proceeding or reporting — log it so the
        # message is never silently dropped from the decision log.
        Clock.unschedule(self._tick)
        save_decision(
            "dismissed",
            self.current_message,
            self.current_risk_score,
            self.current_delay,
            self.q1_answer,
            self.q2_answer,
            dominant_tactic=self.current_dominant_tactic,
        )
        home = self.manager.get_screen("home")
        home.refresh_stats()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"


class AttentionTaskScreen(Screen):
    """
    A simple go / no-go style attention task.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.total_trials = 12
        self.current_trial = 0

        self.awaiting_stimulus = False
        self.response_open = False
        self.current_trial_type = None   # "go" or "no_go"
        self.stimulus_time = None
        self.response_event = None
        self.stimulus_event = None
        self.timeout_event = None
        self.finished = False

        self.go_results = []
        self.false_starts = 0
        self.omission_errors = 0
        self.commission_errors = 0

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        add_bg(root, BG0)

        header = HeaderBar(title="ATTENTION TASK", show_back=True, on_back=self._back)

        self.info_lbl = Label(
            text="Press Start. Tap only when the screen says TAP NOW.",
            color=TEXT_PRI,
            halign="center",
            valign="middle",
        )
        self.info_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.progress_lbl = Label(
            text="Trials completed: 0/12",
            color=TEXT_SEC,
            size_hint_y=None,
            height=dp(24),
        )

        self.signal_lbl = Label(
            text="READY",
            color=C_BLUE,
            font_size=dp(28),
            bold=True,
            size_hint_y=None,
            height=dp(60),
        )

        self.result_lbl = Label(
            text="",
            color=C_AMBER,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(90),
        )
        self.result_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.tap_btn = Button(
            text="Start",
            size_hint_y=None,
            height=dp(60),
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 1),
        )
        self.tap_btn.bind(on_press=self._handle_tap)

        for w in (header, self.info_lbl, self.progress_lbl, self.signal_lbl, self.result_lbl, self.tap_btn):
            root.add_widget(w)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        """Reset the task to its initial state each time the screen is entered."""
        self._reset_task()

    def _reset_task(self):
        """Clear all trial data and return UI to the pre-start state."""
        Clock.unschedule(self._show_stimulus)
        Clock.unschedule(self._close_response_window)

        self.current_trial = 0
        self.awaiting_stimulus = False
        self.response_open = False
        self.current_trial_type = None
        self.stimulus_time = None
        self.finished = False

        self.go_results = []
        self.false_starts = 0
        self.omission_errors = 0
        self.commission_errors = 0

        self.info_lbl.text = "Press Start. Tap only when the screen says TAP NOW."
        self.progress_lbl.text = f"Trials completed: 0/{self.total_trials}"
        self.signal_lbl.text = "READY"
        self.signal_lbl.color = C_BLUE
        self.result_lbl.text = ""
        self.tap_btn.text = "Start"

    def _handle_tap(self, *_):
        """Handle every tap on the main button, routing to the correct action.
        """
        if self.finished:
            # Task complete — restart on next tap.
            self._reset_task()
            return

        if not self.awaiting_stimulus and not self.response_open:
            # Idle state (between trials or at start) — advance to next trial.
            self._start_next_trial()
            return

        # tapped too early, before stimulus appears
        if self.awaiting_stimulus and not self.response_open:
            self.false_starts += 1
            self.info_lbl.text = "Too early. Wait for the signal."
            self.result_lbl.text = (
                f"False starts: {self.false_starts}\n"
                f"Commission errors: {self.commission_errors}\n"
                f"Omission errors: {self.omission_errors}"
            )
            self.signal_lbl.text = "TOO EARLY"
            self.signal_lbl.color = C_AMBER

            # Cancel the scheduled stimulus and reset to idle so the user
            # can tap "Continue" to move on.
            Clock.unschedule(self._show_stimulus)
            self.awaiting_stimulus = False
            self.tap_btn.text = "Continue"
            return

        if self.response_open:
            # Response window is open — evaluate the tap.
            Clock.unschedule(self._close_response_window)

            # correct go response
            if self.current_trial_type == "go":
                rt_ms = int((time.time() - self.stimulus_time) * 1000)
                self.go_results.append(rt_ms)
                self.result_lbl.text = (
                    f"Correct tap\n"
                    f"Reaction time: {rt_ms} ms"
                )
                self.signal_lbl.text = "GOOD"
                self.signal_lbl.color = ACCENT

            # commission error on no-go
            elif self.current_trial_type == "no_go":
                self.commission_errors += 1
                self.false_starts += 1  # stored together for compatibility with current storage.py
                self.result_lbl.text = (
                    "Tapped on a NO TAP trial\n"
                    f"Commission errors: {self.commission_errors}"
                )
                self.signal_lbl.text = "NO TAP!"
                self.signal_lbl.color = C_RED

            self._finish_trial()

    def _start_next_trial(self):
        """Set up the next trial: flip flags and schedule the random-delay stimulus."""
        if self.current_trial >= self.total_trials:
            self._finish_task()
            return

        self.awaiting_stimulus = True
        self.response_open = False
        self.current_trial_type = None
        self.stimulus_time = None

        self.info_lbl.text = "Wait for the next signal..."
        self.signal_lbl.text = "WAIT"
        self.signal_lbl.color = C_BLUE
        self.tap_btn.text = "Tap"
        delay = random.uniform(1.2, 2.5)
        self.stimulus_event = Clock.schedule_once(self._show_stimulus, delay)

    def _show_stimulus(self, dt):
        """Display either a GO (tap) or NO-GO (withhold) signal.
        """
        self.awaiting_stimulus = False
        self.response_open = True

        # 75% go, 25% no-go
        self.current_trial_type = "go" if random.random() < 0.75 else "no_go"
        self.stimulus_time = time.time()

        if self.current_trial_type == "go":
            self.signal_lbl.text = "TAP NOW"
            self.signal_lbl.color = ACCENT
            self.info_lbl.text = "Tap now."
        else:
            self.signal_lbl.text = "DO NOT TAP"
            self.signal_lbl.color = C_RED
            self.info_lbl.text = "Do not tap."

        self.timeout_event = Clock.schedule_once(self._close_response_window, 1.0)

    def _close_response_window(self, dt):
        """Handle trial timeout: score as omission (GO) or correct withhold (NO-GO)."""
        if not self.response_open:
            return

        self.response_open = False

        # missed a go trial
        if self.current_trial_type == "go":
            self.omission_errors += 1
            self.result_lbl.text = (
                "Missed a TAP trial\n"
                f"Omission errors: {self.omission_errors}"
            )
            self.signal_lbl.text = "MISSED"
            self.signal_lbl.color = C_AMBER

        elif self.current_trial_type == "no_go":
            self.result_lbl.text = "Correctly ignored NO TAP"
            self.signal_lbl.text = "GOOD"
            self.signal_lbl.color = ACCENT

        self._finish_trial()

    def _finish_trial(self):
        """Increment trial counter, update progress, and decide whether to end the task."""
        self.current_trial += 1
        self.progress_lbl.text = f"Trials completed: {self.current_trial}/{self.total_trials}"

        if self.current_trial < self.total_trials:
            # More trials remaining — set button to advance to the next one.
            self.tap_btn.text = "Next Trial"
            self.awaiting_stimulus = False
            self.response_open = False
        else:
            self._finish_task()

    def _finish_task(self):
        self.finished = True

        # Save only correct GO RTs and false_starts for compatibility
        state = save_attention_summary(
            results=self.go_results,
            false_starts=self.false_starts,
            commission_errors=self.commission_errors,
            omission_errors=self.omission_errors,
            total_trials=self.total_trials,
        )

        avg_ms = state.get("reaction_avg_ms")
        impulsivity_level = state.get("impulsivity_level", "unknown")

        self.info_lbl.text = "Attention task complete."
        self.signal_lbl.text = "DONE"
        self.signal_lbl.color = C_BLUE
        self.result_lbl.text = (
            f"Avg GO RT: {avg_ms} ms\n"
            f"False starts: {self.false_starts}\n"
            f"Commission errors: {self.commission_errors}\n"
            f"Omission errors: {self.omission_errors}\n"
            f"Level: {impulsivity_level}"
        )
        self.tap_btn.text = "Restart"

    def _back(self, *_):
        Clock.unschedule(self._show_stimulus)
        Clock.unschedule(self._close_response_window)
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"


class RootLayout(BoxLayout):
    """Top-level layout: ScreenManager stacked above the persistent BottomNav bar."""
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        add_bg(self, BG0)

        self.sm = ScreenManager()

        # Instantiate all screens up front so navigation between them is instant.
        self.home = HomeScreen(name="home")
        self.prefs = PreferencesScreen(name="prefs")
        self.intervention = InterventionScreen(name="intervention")
        self.attention = AttentionTaskScreen(name="attention")
        self.reward = RewardTaskScreen(name="reward")

        for screen in (self.home, self.prefs, self.intervention, self.attention, self.reward):
            self.sm.add_widget(screen)

        self.nav = BottomNav(on_nav=self._nav)
        self.add_widget(self.sm)
        self.add_widget(self.nav)

    def _nav(self, key):
        """Switch the active screen and sync the bottom nav tab highlight."""
        self.nav.set_active(key)
        self.sm.transition = SlideTransition(direction="left" if key != "home" else "right")
        self.sm.current = key


class RewardTaskScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.trials = [
            {
                "text": "Congratulations! You won a $1000 gift card. Claim now.",
                "reward_lure": True,
            },
            {
                "text": "You have been selected for a free iPhone. Confirm delivery.",
                "reward_lure": True,
            },
            {
                "text": "Amazon Deal: 80% off today only. Tap to claim discount.",
                "reward_lure": True,
            },
            {
                "text": "Your bank account was suspended. Verify immediately.",
                "reward_lure": False,
            },
            {
                "text": "IRS NOTICE: Unpaid tax detected. Pay now to avoid penalty.",
                "reward_lure": False,
            },
            {
                "text": "Hey, are you still coming to dinner tonight?",
                "reward_lure": False,
            },
        ]

        self.index = 0
        self.risky_opens = 0
        self.safe_choices = 0
        self.finished = False

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        add_bg(root, BG0)

        header = HeaderBar(title="REWARD TASK", show_back=True, on_back=self._back)

        self.info_lbl = Label(
            text="Decide what you would do with each message.",
            color=TEXT_SEC,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(50),
        )
        self.info_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.progress_lbl = Label(
            text="Message 1/6",
            color=TEXT_DIM,
            size_hint_y=None,
            height=dp(24),
        )

        self.message_lbl = Label(
            text="",
            color=TEXT_PRI,
            font_size=dp(16),
            halign="center",
            valign="middle",
        )
        self.message_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.open_btn = Button(
            text="Open / Claim",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.45, 0.20, 0.12, 1),
        )
        self.ignore_btn = Button(
            text="Ignore",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.18, 0.24, 0.30, 1),
        )
        self.report_btn = Button(
            text="Report Suspicious",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.45, 0.10, 0.10, 1),
        )

        self.result_lbl = Label(
            text="",
            color=C_AMBER,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(90),
        )
        self.result_lbl.bind(size=lambda i, v: setattr(i, "text_size", v))

        self.open_btn.bind(on_press=lambda *_: self._answer("open"))
        self.ignore_btn.bind(on_press=lambda *_: self._answer("ignore"))
        self.report_btn.bind(on_press=lambda *_: self._answer("report"))

        for w in (
            header,
            self.info_lbl,
            self.progress_lbl,
            self.message_lbl,
            self.open_btn,
            self.ignore_btn,
            self.report_btn,
            self.result_lbl,
        ):
            root.add_widget(w)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        """Shuffle trials and reset counters each time the screen is entered."""
        self._reset_task()

    def _reset_task(self):
        """Re-randomise the trial order and clear all per-run counters."""
        random.shuffle(self.trials)
        self.index = 0
        self.risky_opens = 0
        self.safe_choices = 0
        self.finished = False
        self.result_lbl.text = ""
        self.open_btn.disabled = False
        self.ignore_btn.disabled = False
        self.report_btn.disabled = False
        self._show_trial()

    def _show_trial(self):
        """Display the current trial message, or end the task if all trials are done."""
        if self.index >= len(self.trials):
            self._finish_task()
            return

        trial = self.trials[self.index]
        self.progress_lbl.text = f"Message {self.index + 1}/{len(self.trials)}"
        self.message_lbl.text = trial["text"]

    def _answer(self, choice):
        """Record the user's choice for the current trial and advance.
        """
        if self.finished:
            return

        trial = self.trials[self.index]

        # Only opening a reward-lure message counts as a risky open.
        # Ignoring or reporting any message — risky or not — counts as safe.
        if trial["reward_lure"] and choice == "open":
            self.risky_opens += 1
        elif choice in ("ignore", "report"):
            self.safe_choices += 1

        self.index += 1
        self._show_trial()

    def _finish_task(self):
        """Persist results, compute scores, and display the summary."""
        self.finished = True

        state = save_reward_summary(
            risky_opens=self.risky_opens,
            safe_choices=self.safe_choices,
            total_trials=len(self.trials),
        )

        reward_score = state.get("reward_score")
        behavioral_score = state.get("behavioral_intervention_score")

        self.message_lbl.text = "Reward task complete."
        self.progress_lbl.text = "Done"
        self.result_lbl.text = (
            f"Risky reward opens: {self.risky_opens}\n"
            f"Safe choices: {self.safe_choices}\n"
            f"Reward Score: {reward_score}/100\n"
            f"Behavioral Score: {behavioral_score}/100"
        )

        # Disable action buttons so the user can't accidentally submit more answers.
        self.open_btn.disabled = True
        self.ignore_btn.disabled = True
        self.report_btn.disabled = True

    def _back(self, *_):
        """Navigate back to the home screen."""
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"


class RunApp(App):
    title = "NoRush"

    def build(self):
        """Build and return the root widget; called once by the Kivy framework."""
        Window.clearcolor = BG0
        self._root_layout = RootLayout()
        return self._root_layout

    def on_start(self):
        """Start the SMS receiver after the UI is fully initialised.

        Called by Kivy after build() completes and the window is shown.
        """
        home = self._root_layout.home
        self._receiver = create_receiver_for_app(home)
        self._receiver.start(home.receive_sms)

    def on_stop(self):
        """Clean up the SMS receiver when the app is closed or backgrounded."""
        if hasattr(self, "_receiver"):
            self._receiver.stop()


def main():
    RunApp().run()


if __name__ == "__main__":
    main()
