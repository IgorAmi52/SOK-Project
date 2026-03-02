from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
	data_sources: list[dict[str, str]] = []
	visualizers: list[dict[str, str]] = []
	integration_message = "Platform package is not installed yet."

	try:
		from graph_platform.app import create_plugin_registry

		registry = create_plugin_registry()
		data_sources = [
			{"id": plugin.plugin_id, "name": plugin.display_name}
			for plugin in registry.list_data_sources()
		]
		visualizers = [
			{"id": plugin.plugin_id, "name": plugin.display_name}
			for plugin in registry.list_visualizers()
		]
		integration_message = "Platform registry loaded successfully."
	except Exception as ex:
		integration_message = f"Platform integration pending: {ex}"

	return render(
		request,
		"main/home.html",
		{
			"integration_message": integration_message,
			"data_sources": data_sources,
			"visualizers": visualizers,
		},
	)
