import wx
from wx import html
from displayframe import DisplayFrame
from tooltip import PermanentTooltip
import versetree


from swlib.pysw import VK, VerseParsingError
from backend.book import GetVerseStr, GetBookChapter, GetBestRange
from util import util
from util.util import ReplaceUnicode
from util.debug import *
from gui import guiutil
import config
import guiconfig
from moduleinfo import ModuleInfo
from gui.menu import MenuItem, Separator
from dictionarylist import DictionarySelector
from gui.quickselector import QuickSelector

from events import SETTINGS_CHANGED, CHAPTER_MOVE, VERSE_MOVE, QUICK_SELECTOR


class BookFrame(DisplayFrame):
	has_menu = True
	shows_info = True
	use_quickselector = True
	def __init__(self, parent, style=html.HW_DEFAULT_STYLE):
		super(BookFrame, self).__init__(parent, style=style)
		self.reference = ""
		self.setup()

	def notify(self, ref, source=None):
		self.SetReference(ref)

	def SetBook(self, book):
		self.book = book

	def SetMod(self, book):
		self.book.SetModule(book)

	def SetPage(self, *args, **kwargs):
		# close all open tooltips
		guiconfig.mainfrm.hide_tooltips()
		return super(BookFrame, self).SetPage(*args, **kwargs)

	def get_verified_one_verse(self, ref):
		try:
			ref = str(GetVerseStr(ref, self.reference, raiseError=True))
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(str(e), config.name)
		
	def get_verified_multi_verses(self, ref):
		try:
			ref = str(GetBestRange(ref, self.reference, raiseError=True))
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(str(e), config.name)	
		


	@guiutil.frozen
	def SetReference(self, ref, context=None, raw=None):
		if raw is None:
			raw = config.raw
		self.reference = ref
		text = self.book.GetReference(ref, context=context, raw=raw)#bible text
		if text is None:
			data = config.MODULE_MISSING_STRING
		else:
			data = text
			data = data.replace("<!P>","</p><p>")
			if True:#:wx.USE_UNICODE:
				#replace common values
				data = ReplaceUnicode(data)
		self.SetPage(data, raw=raw)
		self.update_title()
		

	def setup(self):
		self.book = None
		
		super(BookFrame, self).setup()
	
	def get_actions(self):
		actions = super(BookFrame, self).get_actions()
		actions.update({
			wx.WXK_F8: self.chapter_forward,
			wx.WXK_F5: self.chapter_back,
			ord("T"): self.tooltip_quickly,
		})

		if self.use_quickselector:
			actions[ord("G")] = self.go_quickly
		
		return actions

	def chapter_move(self, amount): pass

	def chapter_forward(self):
		"""Move to next article"""
		self.chapter_move(1)
	
	def chapter_back(self):
		"""Move to previous article"""
		self.chapter_move(-1)
	
	def reload(self):
		self.SetReference(self.reference)

	def toggle_frame(self):
		"""Shows or hides the frame"""
		pane = guiconfig.mainfrm.get_pane_for_frame(self)
		guiconfig.mainfrm.show_panel(pane.name, not pane.IsShown())
	
	def is_hidable(self):
		pane = guiconfig.mainfrm.get_pane_for_frame(self)

		return pane.HasCloseButton()

	def get_menu_items(self):
		def set_text():
			pane = guiconfig.mainfrm.get_pane_for_frame(self)
			if not pane.IsShown():
				return "Show the '%s' frame" % pane.name
			else:
				return "Hide the '%s' frame" % pane.name

		extras = ()
		if self.is_hidable():
			extras += (
				MenuItem("Show this frame", self.toggle_frame, 
					update_text=set_text),
				Separator
			)
		
		items = extras + super(BookFrame, self).get_menu_items()
		if self.shows_info:
			items += (
			Separator,
			MenuItem("Information...", self.show_module_information,
				enabled=self.has_module),
		)

		return items
	
			
	def has_module(self):
		return self.book.mod is not None
	
	def show_module_information(self):
		"""Show information on the current module"""
		ModuleInfo(guiconfig.mainfrm, self.book.mod).ShowModal()
		
	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		version = self.book.version
		ref = self.reference
		text = "%s - %s (%s)" % (p.name, ref, version)
		m.set_pane_title(p.name, text)		
	
	def get_window(self):
		return self

	def go_quickly(self):
		qs = QuickSelector(self.get_window(), 
			title="Go to reference")

		qs.pseudo_modal(self.go_quickly_finished)
	
	def tooltip_quickly(self):
		qs = QuickSelector(self.get_window(), 
			title="Open sticky tooltip")

		qs.pseudo_modal(self.tooltip_quickly_finished)
		
	def tooltip_quickly_finished(self, qs, ansa):
		if ansa == wx.OK:
			text = self.get_verified_multi_verses(qs.text)
			if text:
				self.open_tooltip(text)
				
		qs.Destroy()
	
	def open_tooltip(self, ref):
		tooltip = PermanentTooltip(guiconfig.mainfrm,
			html_type=DisplayFrame, is_biblical=True,)
			
		tooltip.set_ref(ref)
		tooltip.ShowTooltip()
	
	def go_quickly_finished(self, qs, ansa):
		if ansa == wx.OK:
			ref = self.get_verified(qs.text)
			if ref:
				self.notify(ref, source=QUICK_SELECTOR)

		qs.Destroy()

		# and move focus back to ourselves
		self.SetFocus()
	
	def get_verified(self, ref):
		return ref


	
class VerseKeyedFrame(BookFrame):
	def chapter_move(self, number):
		vk = VK(self.reference)
		vk.chapter += number
		if not vk.Error():
			self.notify(vk.text, source=CHAPTER_MOVE)
	
	def verse_move(self, number):
		vk = VK(self.reference)
		vk += number
		self.notify(vk.text, source=VERSE_MOVE)
	
	def get_actions(self):
		d = super(VerseKeyedFrame, self).get_actions()
		d.update({wx.WXK_F9 : self.verse_back,
				  wx.WXK_F12: self.verse_forward,
		})

		return d
	
		

		
	def verse_forward(self):
		"""Move forward a verse"""
		self.verse_move(1)
	
	def verse_back(self):
		"""Move back a verse"""
		self.verse_move(-1)
	
	def chapter_forward(self):
		"""Move to next chapter"""
		self.chapter_move(1)
	
	def chapter_back(self):
		"""Move to previous chapter"""
		self.chapter_move(-1)
	
	get_verified = BookFrame.get_verified_one_verse

class LinkedFrame(VerseKeyedFrame):
	def __init__(self, parent):
		self.panel = wx.Panel(parent)
		self.linked = False
		super(LinkedFrame, self).__init__(self.panel)

		self.create_toolbar()
		sizer = wx.BoxSizer(wx.VERTICAL)
		si = sizer.Add(self.toolbar, flag=wx.GROW)
		sizer.SetItemMinSize(self.toolbar, self.toolbar.MinSize)
		sizer.Add(self, 3, flag=wx.GROW)
		self.panel.SetSizer(sizer)
		self.panel.Fit()

		guiconfig.mainfrm.bible_observers += self.bible_ref_changed
		
	
	def create_toolbar(self):
		self.toolbar = wx.ToolBar(self.panel, style=wx.TB_FLAT)
		self.gui_reference = versetree.VerseTree(self.toolbar)
		self.gui_reference.SetSize((140, -1))
		
		#self.gui_reference = wx.TextCtrl(self.toolbar,
		#		style=wx.TE_PROCESS_ENTER)
		
		self.gui_go = self.toolbar.AddTool(wx.ID_ANY,  
			guiutil.bmp("accept.png"),
			shortHelpString="Open this reference")

		self.toolbar.AddSeparator()
		
		self.gui_link = self.toolbar.AddCheckTool(wx.ID_ANY,
			guiutil.bmp("link.png"), 
			shortHelp="Link the %s to the Bible" % self.title)

		self.linked = True
		self.toolbar.ToggleTool(self.gui_link.Id, True)

		self.toolbar.InsertControl(0, self.gui_reference)
		
		#self.set_link()
		self.toolbar.Realize()
		

		self.toolbar.MinSize = self.toolbar.Size		
		self.toolbar.Bind(wx.EVT_TOOL, self.set_ref, id=self.gui_go.Id)
		self.toolbar.Bind(wx.EVT_TOOL, self.on_link, id=self.gui_link.Id)
		self.gui_reference.Bind(wx.EVT_TEXT_ENTER, self.set_ref)
		
	
	def set_ref(self, event):
		ref = self.gui_reference.Value
		if not ref: return
		ref = self.get_verified(str(ref))
		if not ref: return
		self.SetReference(ref)
	
	def set_link(self):
		print "set_link"
		help = ["Link the %s to the Bible", 
				"Unlink the %s from the Bible"]

		self.linked = not self.linked
		picts = ["link.png", "link_break.png"]
		pic = config.graphics_path + picts[self.linked] 

		self.gui_link.ShortHelp = help[self.linked] % self.title
		self.gui_link.Tooltip = help[self.linked] % self.title
		
		self.gui_link.SetBitmap1(wx.BitmapFromImage(wx.Image(pic)))
		self.toolbar.Realize()
	
	def on_link(self, event=None):
		self.linked = not self.linked
		#self.set_link()
		if self.linked:
			self.SetReference(guiconfig.mainfrm.currentverse)
	
	def bible_ref_changed(self, event):
		if self.linked:
			self.SetReference(event.ref)

		elif event.settings_changed:
			# BUG: unknown member refresh
			self.refresh()

	def get_window(self):
		return self.panel


class CommentaryFrame(LinkedFrame):
	title = "Commentary"

	def __init__(self, parent, book):
		super(CommentaryFrame, self).__init__(parent)
		self.SetBook(book)

	def SetReference(self, ref, context = None):
		super(CommentaryFrame, self).SetReference(ref)
		
		self.gui_reference.SetValue(ref)
		self.gui_reference.currentverse = ref
		
	

class DictionaryFrame(BookFrame):
	title = "Dictionary"

	def __init__(self, parent, book):
		self.dict = wx.Panel(parent)
		self.dictsplitter = wx.SplitterWindow(self.dict)
		
		#self = DictionaryFrame(self.dictsplitter, self)
		super(DictionaryFrame, self).__init__(self.dictsplitter)
		self.SetBook(book)
		

		self.dictionary_list = DictionarySelector(self.dictsplitter, book)
		s = wx.BoxSizer(wx.HORIZONTAL)
		#s.Add(self.dictionarytext, proportion=1, flag = wx.EXPAND)
		#s.Add(self.dictionary_list, 0, wx.GROW)
		self.dictsplitter.SetSashGravity(1)
		self.dictsplitter.SplitVertically(self,
						self.dictionary_list)
		
		self.dictsplitter.SetMinimumPaneSize(100)
		
		def set_splitter():
			self.dictsplitter.SetSashPosition(self.dictsplitter.Size[0] - 130)

		wx.CallAfter(set_splitter)
						
		
		s.Add(self.dictsplitter, 1, wx.GROW)
		self.dict.SetSizer(s)
		#self.dict.Fit()
#		self.dictionary_list = xrc.XRCCTRL(self, 'DictionaryValue')
		#self.Center()
	

	def chapter_move(self, amount):
		mod = self.book.mod
		if not mod:
			return

		key = mod.getKey()
		key.Persist(1)
		key.setText(self.reference)
		mod.setKey(key)
		#while(not ord(self.mod.Error())):
		#		topics.append(self.mod.getKeyText());
		mod.increment(amount);
		ref = mod.getKeyText()
		self.notify(ref, source=CHAPTER_MOVE)
	
	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		version = self.book.version
		ref = self.reference
		text = "%s - %s (%s)" % (p.name, self.book.snap_text(ref), version)
		m.set_pane_title(p.name, text)
	
	def get_window(self):
		return self.dict
		
	
	def notify(self, ref, source=None):
		guiconfig.mainfrm.UpdateDictionaryUI(ref)
		

#xrc_classes = [DictionaryFrame, CommentaryFrame, BookFrame, BibleFrame]
#
#for a in xrc_classes:
#	exec """class %(name)sXRC(%(name)s):
#	def __init__(self):
#		pre = html.PreHtmlWindow()
#		self.PostCreate(pre)
#		self.setup()
#	def LinkClicked(self, link):
#		%(name)s.LinkClicked(self, link)""" % {"name": a.__name__}
	