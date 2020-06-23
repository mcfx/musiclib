function emit_download(url) {
	let aTag = document.createElement('a');
	aTag.download = '';
	aTag.href = url;
	aTag.click()
}

const ap = new APlayer({
	container: document.getElementById('aplayer'),
	fixed: true,
	mode: 'random',
	preload: 'auto',
	volume: 0.7,
	mutex: true,
	listFolded: true,
	listMaxHeight: 90,
	audio: []
});

function setPlayList(tracks, cur_play = 0, id_only = false) {
	axios.get('/api/songs/' + (id_only ? tracks : tracks.map(track => track.id)).join() + '/play' + (id_only ? '/full' : '')).then(response => {
		var data = response.data.data, files = data.files, covers = data.covers, titles = data.titles, artists = data.artists, al = [];
		try { ap.list.clear(); } catch(e) {}
		for (var i = 0; i < tracks.length; i++) {
			al.push({
				name: id_only ? titles[i] : tracks[i].title,
				artist: id_only ? artists[i] : tracks[i].artist,
				url: files[i],
				cover: covers[i]
			})
		}
		ap.list.add(al);
		ap.list.switch(cur_play);
		ap.play();
	})
}

function getFormatString(album) {
	var tmp = album.quality + (album.quality_details ? ' (' + album.quality_details + ')' : '');
	if (!tmp) return album.format;
	if (!album.format) return tmp;
	return album.format + ', ' + tmp;
}

function getSourceString(album) {
	if (album.source && album.file_source) return album.source + ', ' + album.file_source;
	return album.source || album.file_source;
}

function getDurationString(x) {
	if (x >= 3600) return parseInt(x / 3600).toString() + ':' + ('0' + parseInt(x / 60) % 60).substr(-2) + ':' + ('0' + x % 60).substr(-2);
	return ('0' + parseInt(x / 60)).substr(-2) + ':' + ('0' + x % 60).substr(-2);
}

function download_song(item) {
	axios.get('/api/song/' + item.id + '/link').then(response => {
		emit_download(response.data.data.file_flac || response.data.data.file);
	})
}

const opts = { dark: false };
Vue.use(Vuetify);
Vue.use(VueViewer.default);
Vue.use(VueContextMenu);

const Index = { template: '<div>test index</div>' }

Vue.component('text-edit', {
	template: `
	<span style="width:100%">
		<v-text-field v-model="text" v-if="editing" @blur="stop_edit" @input="debouncedPush()"></v-text-field>
		<span v-else> {{ text }} <v-btn text icon small><v-icon @click="start_edit">mdi-pencil</v-icon></v-btn></span>
		<slot></slot>
	</span>
	`,
	props: ['text', 'pushurl', 'pushkey'],
	data: function() {
		return {
			editing: false
		}
	},
	created: function() {
		this.debouncedPush = _.debounce(() => { this.push() }, 150)
	},
	methods: {
		start_edit: function() {
			this.editing = true
		},
		stop_edit: function() {
			this.editing = false;
			this.push();
		},
		push: function() {
			var data = {};
			data[this.pushkey] = this.text;
			axios.post(this.pushurl, data);
		}
	}
})

Vue.component('log-file', {
	template: `
	<div>
		{{ filename.substr(-12) }} <v-btn text icon small v-on:click="download_log()"><v-icon>mdi-download</v-icon></v-btn>
		<v-textarea :value="file_content" style="font-size:10px" rows="25" no-resize readonly></v-textarea>
	</div>
	`,
	props: ['filename'],
	data: function() {
		return {
			file_content: ''
		}
	},
	created: function() {
		axios.get('/api/log/' + this.filename).then(response => {
			this.file_content = response.data.data;
		})
	},
	methods: {
		download_log: function() {
			axios.get('/api/log/' + this.filename + '/download').then(response => {
				emit_download(response.data.data);
			})
		}
	}
})

Vue.component('scans', {
	template: `
	<div>
		<v-card-title>
			<text-edit :text="scan.packname" :pushurl="'/api/scan/' + scan.id + '/update_name'" pushkey="name">
				<v-btn text icon small @click="del"><v-icon>mdi-delete</v-icon></v-btn>
			</text-edit>
		</v-card-title>
		<v-card-text>
			<div v-viewer="{url: 'data-src'}">
				<v-row>
					<v-col cols="2" v-for="img in scan.files">
						<v-card flat>
							<img :src="img[1]" :data-src="img[2]" style="width:100%" :key="'scan_preview_' + img[1] + '_' + img[2]"></img>
							<v-card-text class="text-center">{{ img[0] }}</v-card-text>
						</v-card>
					</v-col>
				</v-row>
			</div>
		</v-card-text>
		<delete-confirm ref="delete_confirm"></delete-confirm>
	</div>
	`,
	props: ['scan'],
	methods: {
		del: function() {
			var album = this.$parent.$parent.$parent.$parent;
			this.$refs.delete_confirm.start('scan', this.scan.id, this.scan.packname, 0, album.init.bind(album))
		}
	}
})

Vue.component('file-links', {
	template: `
	<div>
		<v-card-text v-for="item in files">
			{{ item.name }}
			<v-btn text icon small v-on:click="download(item)" :key="'other_files_' + item.id"><v-icon>mdi-download</v-icon></v-btn>
		</v-card-text>
	</div>
	`,
	props: ['albumid'],
	data: function() {
		return {
			files: []
		}
	},
	created: function() {
		axios.get('/api/album/' + this.albumid + '/files').then(response => {
			this.files = response.data.data;
		})
	},
	methods: {
		download: function(item) {
			emit_download('/filebk/' + item.file + '?dlname=' + item.name)
		}
	}
})

Vue.component('file-upload', {
	template: `
	<v-card-text>
		<v-file-input :label="label" @change="upload($event)"></v-file-input>
		<v-alert dense :type="alert_type" :icon="alert_icon" v-if="alert_visible"> {{ alert_msg }} </v-alert>
	</v-card-text>
	`,
	props: ['label', 'upload_handler'],
	data: function() {
		return {
			alert_type: '',
			alert_icon: '',
			alert_visible: '',
			alert_msg: ''
		}
	},
	methods: {
		upload: function(e) {
			var _this = this;
			this.upload_handler(e, function(res) {
				_this.alert_type = res.status ? 'success' : 'error';
				_this.alert_icon = res.status ? 'mdi-check-circle' : 'mdi-alert';
				_this.alert_msg = res.msg;
				_this.alert_visible = true;
				setTimeout(function() {
					_this.alert_visible = false;
				}, 5000);
			})
		}
	}
})

Vue.component('text-submit', {
	template: `
	<v-card-text>
		<v-text-field :label="label" v-model="text"></v-text-field>
		<v-alert dense :type="alert_type" :icon="alert_icon" v-if="alert_visible"> {{ alert_msg }} </v-alert>
		<v-btn class="no-upper-case" outlined @click="submit"> {{ button_text }} </v-btn>
	</v-card-text>
	`,
	props: ['label', 'button_text', 'submit_handler'],
	data: function() {
		return {
			alert_type: '',
			alert_icon: '',
			alert_visible: '',
			alert_msg: '',
			text: '',
		}
	},
	methods: {
		submit: function() {
			var _this = this;
			this.submit_handler(this.text, function(res) {
				_this.alert_type = res.status ? 'success' : 'error';
				_this.alert_icon = res.status ? 'mdi-check-circle' : 'mdi-alert';
				_this.alert_msg = res.msg;
				_this.alert_visible = true;
				setTimeout(function() {
					_this.alert_visible = false;
				}, 5000);
			})
		}
	}
})

Vue.component('add-playlist', {
	template: `
	<div>
		<v-dialog v-model="show" max-width="500" scrollable>
			<v-card style="min-height:600px">
				<v-card-title>Choose target playlist</v-card-title>
				<v-card-text style="height:600px">
					<v-text-field v-model="search" label="Search for playlists" @input="debouncedSearch()"></v-text-field>
					<v-simple-table>
						<thead>
							<tr>
								<th class="text-left">Title</th>
								<th class="text-left">Length</th>
							</tr>
						</thead>
						<tbody style="cursor:pointer">
							<tr v-for="(item, key) in playlists" :key="'playlistadd' + item.id" @click="addTo(item)">
								<td>{{ item.title }}</td>
								<td>{{ item.len_tracks }}</td>
							</tr>
						</tbody>
					</v-simple-table>
				</v-card-text>
			</v-card>
		</v-dialog>
	</div>
	`,
	data: function() {
		return {
			show: false,
			search: '',
			playlists: [],
		}
	},
	created: function() {
		this.debouncedSearch = _.debounce(() => { this.doSearch() }, 150)
	},
	methods: {
		add: function(track) {
			this.show = true;
			this.cur_track = track;
			this.doSearch();
		},
		doSearch: function() {
			axios.get('/api/playlist/search', {params: {query: this.search, page: 0}}).then(response => {
				this.playlists = response.data.data.playlists;
			})
		},
		addTo: function(playlist) {
			axios.post('/api/playlist/' + playlist.id + '/addtrack', {song_id: this.cur_track.id}).then(response => {
				this.show = false
			})
		}
	}
})

Vue.component('delete-confirm', {
	template: `
	<div>
		<v-dialog v-model="show" max-width="300">
			<v-card>
				<v-card-title>Delete confirmation</v-card-title>
				<v-card-text>Are you sure to delete {{ name }}? This operation is irreversible.</v-card-text>
				<v-card-actions>
					<v-spacer></v-spacer>
					<v-btn color="red" text @click="del()" class="no-upper-case">Delete</v-btn>
					<v-btn color="green" text @click="hide()" class="no-upper-case">Cancel</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</div>
	`,
	data: function() {
		return {
			show: false,
			type: '',
			id: 0,
			name: '',
			callbackurl: 0,
			callback: 0,
		}
	},
	methods: {
		start: function(type, id, name, callbackurl = 0, callback = 0) {
			this.type = type;
			this.id = id;
			this.name = name;
			this.callbackurl = callbackurl;
			this.callback = callback;
			this.show = true;
		},
		del: function() {
			axios.post('/api/' + this.type + '/' + this.id + '/del').then(response => {
				if (typeof(this.callbackurl) == 'object') {
					this.$router.push(this.callbackurl)
				} else if (typeof(this.callback) == 'function') {
					this.callback()
				}
			});
			this.hide();
		},
		hide: function() {
			this.show = false;
			this.id = 0;
		}
	}
})

const Album = {
	template: `
	<div>
		<v-row>
			<v-col sm="4"><v-card outlined><v-img :key="cover_default" :src="cover_default"></v-img></v-card></v-col>
			<v-col sm="8">
				<v-card-title> {{ title }} </v-card-title>
				<v-card-text>
					<div v-if="artist"> Artist: {{ artist }} </div>
					<div v-if="release_date"> Release date: {{ release_date }} </div>
					<div v-if="getFormatString(this)"> Format: {{ getFormatString(this) }} </div>
					<div v-if="getSourceString(this)"> Source: {{ getSourceString(this) }} </div>
					Trusted: {{ trusted ? 'yes' : 'no' }} <br>
					<div v-if="comments"> Comments: {{ comments }} </div>
					<v-btn text small @click="edit()" class="no-upper-case">Edit</v-btn>
					<span v-if="format == 'flac'">
						<v-btn text small @click="gen_flac()" class="no-upper-case">Gen Flac</v-btn>
						<span v-if="gen_flac_result.length">{{ gen_flac_result }}</span>
					</span>
					<v-btn text small @click="manage()" class="no-upper-case">Manage</v-btn>
					<v-btn text small @click="$refs.delete_confirm.start('album', id, title, {name: 'albums'})" class="no-upper-case">Delete</v-btn>
				</v-card-text>
			</v-col>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left" style="min-width:130px"></th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in songs" :key="'song' + item.id">
					<td>{{ item.track }}</td>
					<td>
						<v-btn text icon small v-on:click="setPlayList(songs, key)"><v-icon>mdi-play-circle</v-icon></v-btn>
						<v-btn text icon small v-on:click="download_song(item)"><v-icon>mdi-download</v-icon></v-btn>
						<v-btn text icon small v-on:click="$refs.add_playlist.add(item)"><v-icon>mdi-folder-plus</v-icon></v-btn>
					</td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<v-tabs vertical class="v-tab-no-upper-case">
			<v-tab> Covers </v-tab>
			<v-tab> Scans </v-tab>
			<v-tab> Logs </v-tab>
			<v-tab> Other files </v-tab>
			<v-tab> Add files </v-tab>
			<v-tab-item>
				<v-card-text v-if="cover_files.length">
					<div v-viewer>
						<draggable v-model="cover_files" group="cover-files" tag="v-row" @end="update_covers">
							<v-col cols="2" v-for="item in cover_files">
								<v-card flat>
									<img :src="item" style="width:100%" @contextmenu.prevent="current_cover_name = item.substr(6, 10) + '.jpg'; $refs.cover_menu.open()" :key="'cover' + item"></img>
								</v-card>
							</v-col>
						</v-row>
					</div>
				</v-card-text>
				<v-card-text v-else>
					There are no covers for this album now.
				</v-card-text>
				<context-menu id="context-menu" ref="cover_menu" class="no-padding-left">
					<li class="ctx-header">{{ current_cover_name }}</li>
					<li class="ctx-item" @click="$refs.delete_confirm.start('album/' + id + '/cover', current_cover_name, current_cover_name, 0, init.bind(this))">Delete</li>
				</context-menu>
			</v-tab-item>
			<v-tab-item>
				<v-card-text v-if="scans.length">
					<scans v-for="item in scans" :key="'scan' + item.id" :scan="item"></scans>
				</v-card-text>
				<v-card-text v-else>
					There are no scans for this album now.
				</v-card-text>
			</v-tab-item>
			<v-tab-item>
				<v-card-text v-if="log_files.length">
					<log-file v-for="item in log_files" :key="'log' + item" :filename="item"></log-file>
				</v-card-text>
				<v-card-text v-else>
					There are no log files for this album now.
				</v-card-text>
			</v-tab-item>
			<v-tab-item>
				<file-links :albumid="id"></file-links>
			</v-tab-item>
			<v-tab-item>
				<v-card-title>Add cover</v-card-title>
				<file-upload label="File" :upload_handler="upload('cover')"></file-upload>
				<v-card-title>Add scans</v-card-title>
				<file-upload label="File" :upload_handler="upload('scan')"></file-upload>
				<v-card-title>Add log</v-card-title>
				<file-upload label="File" :upload_handler="upload('log')"></file-upload>
				<v-card-title>Add other file</v-card-title>
				<file-upload label="File" :upload_handler="upload('other')"></file-upload>
			</v-tab-item>
		</v-tabs>
		<add-playlist ref="add_playlist"></add-playlist>
		<delete-confirm ref="delete_confirm"></delete-confirm>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			release_date: null,
			artist: '',
			format: '',
			quality: '',
			quality_details: '',
			source: '',
			file_source: '',
			trusted: '',
			log_files: [],
			cover_files: [],
			comments: '',
			songs: [],
			scans: [],
			gen_flac_result: '',
			current_cover_name: '',
		}
	},
	computed: {
		cover_default: function() {
			return this.cover_files.length ? this.cover_files[0] : 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY/j//z8DAAj8Av6IXwbgAAAAAElFTkSuQmCC';
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/album/' + this.id + '/info').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
				document.title = this.title + ' - ' + this.artist + ' - Albums';
			})
			axios.get('/api/album/' + this.id + '/scans').then(response => {
				this.scans = response.data.data;
			})
		},
		edit: function() {
			this.$router.push({ name: 'album_edit', params: { id: this.id } });
		},
		manage: function() {
			this.$router.push({ name: 'album_manage', params: { id: this.id } });
		},
		upload: function(tp) {
			var albumid = this.id;
			return function(file, callback) {
				let formData = new FormData();
				formData.append('file', file);
				axios.post('/api/album/' + albumid + '/upload/' + tp, formData, {headers: {'Content-Type': 'multipart/form-data'}}).then(response => {
					callback(response.data);
				})
			}
		},
		gen_flac: function() {
			axios.post('/api/album/' + this.id + '/gen_flac').then(response => {
				var _this = this;
				this.gen_flac_result = response.data.status ? 'OK' : 'Error';
				setTimeout(function() {
					_this.gen_flac_result = '';
				}, 3000);
			})
		},
		update_covers: function() {
			axios.post('/api/album/' + this.id + '/update_covers', {covers: this.cover_files})
		}
	}
}

const AlbumEdit = {
	template: `
	<div>
		<v-row>
			<v-card-title> Edit: {{ title }} </v-card-title>
			<v-card-text>
				<v-text-field v-model="title" label="Title"></v-text-field>
				<v-text-field v-model="artist" label="Artist"></v-text-field>
				<v-text-field v-model="release_date" label="Release date"></v-text-field>
				<v-text-field v-model="source" label="Source"></v-text-field>
				<v-text-field v-model="file_source" label="File source"></v-text-field>
				<v-text-field v-model="comments" label="Comments"></v-text-field>
				<v-checkbox v-model="trusted" label="Trusted"></v-checkbox>
			</v-card-text>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="item in songs" :key="'song' + item.id">
					<td><v-text-field v-model="item.track"></v-text-field></td>
					<td><v-text-field v-model="item.title"></v-text-field></td>
					<td>{{ item.duration }}</td>
					<td><v-text-field v-model="item.artist"></v-text-field></td>
				</tr>
			</tbody>
		</v-simple-table>
		<v-btn class="no-upper-case" outlined @click="submit">Confirm</v-btn>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			release_date: null,
			artist: '',
			format: '',
			quality: '',
			quality_details: '',
			source: '',
			file_source: '',
			trusted: '',
			log_files: [],
			cover_files: [],
			comments: '',
			songs: []
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/album/' + this.id + '/info').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
				document.title = this.title + ' - ' + this.artist + ' - Edit - Albums';
			})
		},
		submit: function() {
			var tmp = {
				title: this.title,
				release_date: this.release_date,
				artist: this.artist,
				source: this.source,
				file_source: this.file_source,
				comments: this.comments,
				trusted: this.trusted,
				songs: this.songs,
			};
			axios.post('/api/album/' + this.id + '/update', tmp).then(response => {
				this.$router.push({ name: 'album', params: { id: this.id } });
			})
		}
	}
}

const AlbumManage = {
	template: `
	<div>
		<v-row>
			<v-card-title><h3> Manage: {{ title }} </h3></v-card-title>
		</v-row>
		<v-row>
			<v-card-title> Musicbrainz Matches of Album </v-card-title>
			<v-card-text v-if="!album_musicbrainz.length"> No matches </v-card-text>
			<v-card-text v-else>
				<v-select :items="album_musicbrainz" item-value="id" @change="change_musicbrainz_match_album" label="Select match">
					<template v-slot:selection="data">
						{{ getMusicbrainzArtistName(data.item['artist-credit']) + ' - ' + data.item.title + ' (' + data.item.id + ')' }}
					</template>
					<template v-slot:item="data">
						{{ getMusicbrainzArtistName(data.item['artist-credit']) + ' - ' + data.item.title + ' (' + data.item.id + ')' }}
					</template>
				</v-select>
				<div v-if="typeof(album_musicbrainz_match.id) != 'undefined'">
					ID: <a :href="'https://musicbrainz.org/release/' + album_musicbrainz_match.id">{{ album_musicbrainz_match.id }}</a> <br>
					Title: {{ album_musicbrainz_match.title }} <br>
					Artist: {{ getMusicbrainzArtistName(album_musicbrainz_match['artist-credit']) }} <br>
					Release date: {{ album_musicbrainz_match.date }}
					<v-simple-table>
						<thead>
							<tr>
								<th class="text-left">#</th>
								<th class="text-left">Title</th>
								<th class="text-left">Duration</th>
								<th class="text-left">Artist</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="item in album_musicbrainz_match.media[0].tracks" :key="'mbtrack' + item.id">
								<td>{{ item.number }}</td>
								<td>{{ item.title }}</td>
								<td>{{ getDurationString(parseInt(item.length / 1000)) }}</td>
								<td>{{ getMusicbrainzArtistName(item['artist-credit']) }}</td>
							</tr>
						</tbody>
					</v-simple-table>
					<v-btn class="no-upper-case" @click="apply_musicbrainz_to_album" outlined>Apply Musicbrainz Match to Album</v-btn>
					<span v-if="apply_musicbrainz_to_album_result.length">{{ apply_musicbrainz_to_album_result }}</span>
					<v-btn class="no-upper-case" @click="apply_musicbrainz_cover_to_album" outlined>Add Cover from Cover Art Archive</v-btn>
					<span v-if="apply_musicbrainz_cover_to_album_result.length">{{ apply_musicbrainz_cover_to_album_result }}</span>
				</div>
			</v-card-text>
		</v-row>
		<v-row>
			<v-card-title> Musicbrainz Matches of Tracks </v-card-title>
			<v-card-text>
				<v-select :items="songs" item-value="id" @change="change_track" label="Select track">
					<template v-slot:selection="data">
						{{ data.item.track + '. ' + data.item.artist + ' - ' + data.item.title }}
					</template>
					<template v-slot:item="data">
						{{ data.item.track + '. ' + data.item.artist + ' - ' + data.item.title }}
					</template>
				</v-select>
				<div v-if="selected_track">
					<div v-if="!track_musicbrainz.length"> No matches </div>
					<div v-else>
						<v-select :items="track_musicbrainz" item-value="id" @change="change_musicbrainz_match_track" label="Select match">
							<template v-slot:selection="data">
								{{ getMusicbrainzArtistName(data.item['artist-credit']) + ' - ' + data.item.title + ' (' + data.item.id + ')' }}
							</template>
							<template v-slot:item="data">
								{{ getMusicbrainzArtistName(data.item['artist-credit']) + ' - ' + data.item.title + ' (' + data.item.id + ')' }}
							</template>
						</v-select>
						<div v-if="typeof(track_musicbrainz_match.id) != 'undefined'">
							ID: <a :href="'https://musicbrainz.org/recording/' + track_musicbrainz_match.id">{{ track_musicbrainz_match.id }}</a> <br>
							Title: {{ track_musicbrainz_match.title }} <br>
							Artist: {{ getMusicbrainzArtistName(track_musicbrainz_match['artist-credit']) }} <br>
							Duration: {{ getDurationString(parseInt(track_musicbrainz_match.length / 1000)) }} <br>
							<v-btn class="no-upper-case" @click="apply_musicbrainz_to_song" outlined>Apply Musicbrainz Match to Track</v-btn>
							<span v-if="apply_musicbrainz_to_song_result.length">{{ apply_musicbrainz_to_song_result }}</span>
						</div>
					</div>
				</div>
			</v-card-text>
		</v-row>
		<v-row>
			<v-card-title> Match Musicbrainz with Acoustid </v-card-title>
			<v-card-text>
				<v-btn class="no-upper-case" @click="match_acoustid" outlined>Start Analyze</v-btn>
				<span v-if="match_acoustid_result.length">{{ match_acoustid_result }}</span>
			</v-card-text>
		</v-row>
		<v-row>
			<v-card-title> Manually Set Musicbrainz ID for Album </v-card-title>
			<v-card-text>
				<v-text-field label="Musicbrainz ID" v-model="musicbrainz_id"></v-text-field>
				<v-btn class="no-upper-case" @click="set_musicbrainz_id()" outlined>Submit</v-btn>
				<span v-if="set_musicbrainz_id_result.length">{{ set_musicbrainz_id_result }}</span>
			</v-card-text>
		</v-row>
		<v-row>
			<v-card-title> Verify CD with CUETools </v-card-title>
			<v-card-text>
				<v-btn class="no-upper-case" @click="cuetools_verify" outlined>Start Verify</v-btn>
				<span v-if="cuetools_verify_result.length">{{ cuetools_verify_result }}</span>
			</v-card-text>
			<v-card-text>
				<v-textarea :value="extra_data.cuetools || ''" style="font-size:10px" rows="25" label="CUETools Results" no-resize readonly outlined></v-textarea>
			</v-card-text>
		</v-row>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			release_date: null,
			artist: '',
			format: '',
			quality: '',
			quality_details: '',
			source: '',
			file_source: '',
			trusted: '',
			log_files: [],
			cover_files: [],
			comments: '',
			songs: [],
			extra_data: {},
			match_acoustid_result: '',
			album_musicbrainz_match: {},
			selected_track: null,
			track_musicbrainz: [],
			track_musicbrainz_match: {},
			musicbrainz_id: '',
			set_musicbrainz_id_result: '',
			cuetools_verify_result: '',
			apply_musicbrainz_to_song_result: '',
			apply_musicbrainz_to_album_result: '',
			apply_musicbrainz_cover_to_album_result: '',
			working: false,
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.working = true;
		console.log('1')
		this.init();
	},
	computed: {
		album_musicbrainz: function() {
			return this.extra_data.musicbrainz || [];
		}
	},
	destroyed: function() {
		this.working = false
	},
	methods: {
		init: function() {
			axios.get('/api/album/' + this.id + '/info?extra_data').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
				document.title = this.title + ' - ' + this.artist + ' - Manage - Albums';
				if (this.working) setTimeout(this.init, 2000);
			})
		},
		set_musicbrainz_id: function() {
			axios.post('/api/album/' + this.id + '/set_musicbrainz_id', {'mid': this.musicbrainz_id}).then(response => {
				var _this = this;
				this.set_musicbrainz_id_result = response.data.status ? 'Added to queue.' : 'Error';
				setTimeout(function() {
					_this.set_musicbrainz_id_result = '';
				}, 3000);
			})
		},
		match_acoustid: function() {
			axios.post('/api/album/' + this.id + '/match_acoustid').then(response => {
				var _this = this;
				this.match_acoustid_result = response.data.status ? 'Added to queue.' : 'Error';
				setTimeout(function() {
					_this.match_acoustid_result = '';
				}, 3000);
			})
		},
		change_musicbrainz_match_album: function(id) {
			for (var i = 0; i < this.album_musicbrainz.length; i++) {
				if (this.album_musicbrainz[i].id == id) {
					this.album_musicbrainz_match = this.album_musicbrainz[i];
				}
			}
		},
		change_track: function(id) {
			for (var i = 0; i < this.songs.length; i++) {
				if (this.songs[i].id == id) {
					this.selected_track = this.songs[i];
					this.track_musicbrainz = this.songs[i].extra_data.musicbrainz || [];
					this.track_musicbrainz_match = {};
				}
			}
		},
		change_musicbrainz_match_track: function(id) {
			for (var i = 0; i < this.track_musicbrainz.length; i++) {
				if (this.track_musicbrainz[i].id == id) {
					this.track_musicbrainz_match = this.track_musicbrainz[i];
				}
			}
		},
		cuetools_verify: function() {
			axios.post('/api/album/' + this.id + '/cuetools_verify').then(response => {
				var _this = this;
				this.cuetools_verify_result = response.data.status ? 'Added to queue.' : 'Error';
				setTimeout(function() {
					_this.cuetools_verify_result = '';
				}, 3000);
			})
		},
		apply_musicbrainz_cover_to_album: function() {
			axios.post('/api/album/' + this.id + '/apply_musicbrainz_cover', {'mid': this.album_musicbrainz_match.id}).then(response => {
				var _this = this;
				this.apply_musicbrainz_cover_to_album_result = response.data.status ? 'Added to queue.' : 'Error';
				setTimeout(function() {
					_this.apply_musicbrainz_cover_to_album_result = '';
				}, 3000);
			})
		},
		apply_musicbrainz_to_album: function() {
			axios.post('/api/album/' + this.id + '/apply_musicbrainz', {'mid': this.album_musicbrainz_match.id}).then(response => {
				var _this = this;
				this.apply_musicbrainz_to_album_result = response.data.status ? 'Done' : 'Error';
				setTimeout(function() {
					_this.apply_musicbrainz_to_album_result = '';
				}, 3000);
			})
		},
		apply_musicbrainz_to_song: function() {
			axios.post('/api/song/' + this.selected_track.id + '/apply_musicbrainz', {'mid': this.track_musicbrainz_match.id}).then(response => {
				var _this = this;
				this.apply_musicbrainz_to_song_result = response.data.status ? 'Done' : 'Error';
				setTimeout(function() {
					_this.apply_musicbrainz_to_song_result = '';
				}, 3000);
			})
		},
		getMusicbrainzArtistName: function(s) {
			return s.map(x => x.name + x.joinphrase).join('')
		}
	}
}

const Albums = {
	template: `
	<div>
		<v-text-field v-model="search" label="Search for albums" @input="debouncedSearch()"></v-text-field>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">Title</th>
					<th class="text-left">Artist</th>
					<th class="text-left">Format</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in albums" :key="'album' + item.id">
					<td><router-link :to="'/album/' + item.id">{{ item.title || 'Empty name' }}</router-link></td>
					<td>{{ item.artist }}</td>
					<td>{{ getFormatString(item) }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<div class="text-center" v-if="count > results_per_page">
			<v-pagination v-model="cur_page" :length="Math.ceil(count / results_per_page)" @input="doSearch"></v-pagination>
		</div>
	</div>
	`,
	data: function() {
		return {
			search: '',
			count: 0,
			cur_page: 1,
			albums: [],
		}
	},
	created: function() {
		this.debouncedSearch = _.debounce(() => { this.cur_page = 1; this.doSearch() }, 150);
		this.doSearch();
	},
	methods: {
		doSearch: function() {
			axios.get('/api/album/search', {params: {query: this.search, page: this.cur_page - 1}}).then(response => {
				this.albums = response.data.data.albums;
				this.count = response.data.data.count;
			})
		}
	}
}

const Songs = {
	template: `
	<div>
		<v-text-field v-model="search" label="Search for albums" @input="debouncedSearch()"></v-text-field>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left" style="min-width:130px"></th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
					<th class="text-left">Album</th>
					<th class="text-left">Format</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in songs" :key="'song' + item.id">
					<td>{{ key + 1 + (cur_show_page - 1) * results_per_page }}</td>
					<td>
						<v-btn text icon small v-on:click="setPlayList(songs, key)"><v-icon>mdi-play-circle</v-icon></v-btn>
						<v-btn text icon small v-on:click="download_song(item)"><v-icon>mdi-download</v-icon></v-btn>
						<v-btn text icon small v-on:click="$refs.add_playlist.add(item)"><v-icon>mdi-folder-plus</v-icon></v-btn>
					</td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
					<td><router-link :to="'/album/' + item.album_id">{{ item.album_title }}</router-link></td>
					<td>{{ getFormatString(item) }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<div class="text-center" v-if="count > results_per_page">
			<v-pagination v-model="cur_page" :length="Math.ceil(count / results_per_page)" @input="doSearch"></v-pagination>
		</div>
		<add-playlist ref="add_playlist"></add-playlist>
	</div>
	`,
	data: function() {
		return {
			search: '',
			count: 0,
			cur_page: 1,
			cur_show_page: 1,
			songs: [],
		}
	},
	created: function() {
		this.debouncedSearch = _.debounce(() => { this.cur_page = 1; this.doSearch() }, 150);
		this.doSearch();
	},
	methods: {
		doSearch: function() {
			axios.get('/api/song/search', {params: {query: this.search, page: this.cur_page - 1}}).then(response => {
				this.songs = response.data.data.songs;
				this.count = response.data.data.count;
				this.cur_show_page = this.cur_page;
			})
		}
	}
}

const Playlist = {
	template: `
	<div>
		<v-row>
			<v-card-title>
				{{ title }} &nbsp;
				<v-btn text icon small><v-icon @click="edit">mdi-pencil</v-icon></v-btn>
				<v-btn text icon small @click="$refs.delete_confirm.start('playlist', id, title, {name: 'playlists'})"><v-icon>mdi-delete</v-icon></v-btn>
			</v-card-title>
			<v-card-text> {{ description }} </v-card-text>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left" style="min-width:130px"></th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
					<th class="text-left">Album</th>
					<th class="text-left">Format</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in tracks" :key="'track' + item.id">
					<td>{{ key + 1 + (cur_show_page - 1) * results_per_page }}</td>
					<td>
						<v-btn text icon small v-on:click="setPlayList(full_tracklist, key + (cur_show_page - 1) * results_per_page , true)"><v-icon>mdi-play-circle</v-icon></v-btn>
						<v-btn text icon small v-on:click="download_song(item)"><v-icon>mdi-download</v-icon></v-btn>
						<v-btn text icon small v-on:click="$refs.add_playlist.add(item)"><v-icon>mdi-folder-plus</v-icon></v-btn>
					</td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
					<td><router-link :to="'/album/' + item.album_id">{{ item.album_title }}</router-link></td>
					<td>{{ getFormatString(item) }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<div class="text-center" v-if="count_tracks > results_per_page">
			<v-pagination v-model="cur_page" :length="Math.ceil(count_tracks / results_per_page)" @input="init"></v-pagination>
		</div>
		<add-playlist ref="add_playlist"></add-playlist>
		<delete-confirm ref="delete_confirm"></delete-confirm>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			description: '',
			count_tracks: 0,
			cur_page: 1,
			cur_show_page: 1,
			tracks: [],
			full_tracklist: ''
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/playlist/' + this.id + '/info/page/' + (this.cur_page - 1)).then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
				this.cur_show_page = this.cur_page;
				document.title = this.title + ' - Playlists';
			})
		},
		edit: function() {
			this.$router.push({ name: 'playlist_edit', params: { id: this.id } });
		}
	}
}

const PlaylistEdit = {
	template: `
	<div>
		<v-row>
			<v-card-title> Edit: {{ title }} </v-card-title>
			<v-card-text>
				<v-text-field v-model="title" label="Title"></v-text-field>
				<v-text-field v-model="description" label="Description"></v-text-field>
			</v-card-text>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
					<th class="text-left">Album</th>
					<th class="text-left"></th>
				</tr>
			</thead>
			<draggable v-model="tracks" group="playlist-tracks" tag="tbody">
				<tr v-for="(item, key) in tracks" :key="'track' + item.id">
					<td>{{ key + 1 }}</td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
					<td>{{ item.album_title }}</td>
					<td><v-btn text icon small v-on:click="tracks.splice(key, 1)"><v-icon>mdi-delete</v-icon></v-btn></td>
				</tr>
			</draggable>
		</v-simple-table>
		<v-card-text><v-btn class="no-upper-case" outlined @click="submit">Confirm</v-btn></v-card-text>
	</div>
	`,
	data: function() {
		return {
			id: -1,
			title: '',
			description: '',
			tracks: []
		}
	},
	created: function() {
		this.id = this.$route.params.id;
		this.init();
	},
	methods: {
		init: function() {
			axios.get('/api/playlist/' + this.id + '/info').then(response => {
				for (key in response.data.data)
					this[key] = response.data.data[key];
				document.title = this.title + ' - Edit - Playlists';
			})
		},
		submit: function() {
			var tmp = {
				title: this.title,
				description: this.description,
				tracks: this.tracks.map(x => x.id).join(),
			};
			axios.post('/api/playlist/' + this.id + '/update', tmp).then(response => {
				this.$router.push({ name: 'playlist', params: { id: this.id } });
			})
		}
	}
}

const Playlists = {
	template: `
	<div>
		<v-text-field v-model="search" label="Search for playlists" @input="debouncedSearch()"></v-text-field>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">Title</th>
					<th class="text-left">Length</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in playlists" :key="'playlist' + item.id">
					<td><router-link :to="'/playlist/' + item.id">{{ item.title }}</router-link></td>
					<td>{{ item.len_tracks }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<div class="text-center" v-if="count > results_per_page">
			<v-pagination v-model="cur_page" :length="Math.ceil(count / results_per_page)" @input="doSearch"></v-pagination>
		</div>
	</div>
	`,
	data: function() {
		return {
			search: '',
			count: 0,
			cur_page: 1,
			playlists: [],
		}
	},
	created: function() {
		this.debouncedSearch = _.debounce(() => { this.cur_page = 1; this.doSearch() }, 150);
		this.doSearch();
	},
	methods: {
		doSearch: function() {
			axios.get('/api/playlist/search', {params: {query: this.search, page: this.cur_page - 1}}).then(response => {
				this.playlists = response.data.data.playlists;
				this.count = response.data.data.count;
			})
		}
	}
}

const Manage = {
	template: `
	<div>
		<v-card-title>Upload album</v-card-title>
		<file-upload label="File" :upload_handler="upload_album"></file-upload>
		<v-card-title>Download album from remote URL</v-card-title>
		<text-submit label="URL" button_text="Download" :submit_handler="upload_album_remote"></text-submit>
		<v-card-title>Create playlist</v-card-title>
		<v-card-text>
			<v-text-field v-model="new_playlist_title" label="title"></v-text-field>
			<v-btn class="no-upper-case" outlined @click="create_playlist">Create</v-btn>
		</v-card-text>
		<v-card-title>Current task</v-card-title>
		<div>
			<v-simple-table v-if="queue.current_task">
				<thead>
					<tr>
						<th class="text-left">Album id</th>
						<th class="text-left">Filename</th>
						<th class="text-left">Path</th>
						<th class="text-left">Type</th>
					</tr>
				</thead>
				<tbody>
					<td>{{ queue.current_task.album_id }}</td>
					<td>{{ queue.current_task.filename }}</td>
					<td>{{ queue.current_task.path }}</td>
					<td>{{ queue.current_task.type }}</td>
				</tbody>
			</v-simple-table>
			<v-card-text v-else>No current task</v-card-text>
		</div>
		<v-card-title>Task queue</v-card-title>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">Album id</th>
					<th class="text-left">Filename</th>
					<th class="text-left">Path</th>
					<th class="text-left">Type</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in queue.queue" :key="'task' + key">
					<td>{{ item.album_id }}</td>
					<td>{{ item.filename }}</td>
					<td>{{ item.path }}</td>
					<td>{{ item.type }}</td>
				</tr>
			</tbody>
		</v-simple-table>
		<v-card-title>Done tasks</v-card-title>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">Album id</th>
					<th class="text-left">Filename</th>
					<th class="text-left">Path</th>
					<th class="text-left">Type</th>
					<th class="text-left">Time</th>
					<th class="text-left">Result</th>
					<th class="text-left">Error</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in queue.done" :key="'taskd' + key">
					<td>{{ item.task.album_id }}</td>
					<td>{{ item.task.filename }}</td>
					<td>{{ item.task.path }}</td>
					<td>{{ item.task.type }}</td>
					<td>{{ item.done_time }}</td>
					<td>{{ item.result.status }}</td>
					<td>{{ item.result.error }}</td>
				</tr>
			</tbody>
		</v-simple-table>
	</div>
	`,
	data: function() {
		return {
			queue: {current_task: null, done: [], queue: []},
			new_playlist_title: '',
			working: false,
		}
	},
	created: function() {
		this.working = true;
		this.init();
	},
	destroyed: function() {
		this.working = false
	},
	methods: {
		init: function(setnxt = true) {
			axios.get('/api/queue').then(response => {
				this.queue = response.data;
				if (this.working && setnxt) setTimeout(this.init, 2000);
			})
		},
		upload_album: function(file, callback) {
			var _this = this;
			let formData = new FormData();
			formData.append('file', file);
			axios.post('/api/album/upload', formData, {headers: {'Content-Type': 'multipart/form-data'}}).then(response => {
				callback(response.data);
				_this.init(false);
			})
		},
		upload_album_remote: function(url, callback) {
			var _this = this;
			axios.post('/api/album/upload/remote', {'url': url}).then(response => {
				callback(response.data);
				_this.init(false);
			})
		},
		create_playlist: function() {
			axios.post('/api/playlist/create', {'title': this.new_playlist_title}).then(response => {
				this.$router.push({ name: 'playlist', params: { id: response.data.id } })
			})
		}
	}
}

const router = new VueRouter({
	mode: vuerouter_history_mode ? 'history' : 'hash',
	routes: [
		{ path: '/', component: Index },
		{ path: '/album/:id', component: Album, name: 'album', meta: {title: route => { return route.params.id + ' - Albums' }}},
		{ path: '/album/:id/edit', component: AlbumEdit, name: 'album_edit', meta: {title: route => { return route.params.id + ' - Edit - Albums' }}},
		{ path: '/album/:id/manage', component: AlbumManage, name: 'album_manage', meta: {title: route => { return route.params.id + ' - Manage - Albums' }}},
		{ path: '/albums', component: Albums, name: 'albums', meta: {title: 'Albums' }},
		{ path: '/songs', component: Songs, name: 'songs', meta: {title: 'Songs' }},
		{ path: '/playlist/:id', component: Playlist, name: 'playlist', meta: {title: route => { return route.params.id + ' - Playlists' }}},
		{ path: '/playlist/:id/edit', component: PlaylistEdit, name: 'playlist_edit', meta: {title: route => { return route.params.id + ' - Edit - Playlists' }}},
		{ path: '/playlists', component: Playlists, name: 'playlists', meta: {title: 'Playlists' }},
		{ path: '/manage', component: Manage, name: 'manage', meta: {title: 'Manage' }},
	]
})

new Vue({
	router,
	el: '#app',
	vuetify: new Vuetify(opts)
})

function updateTemporaryTitle(route) {
	Vue.nextTick(() => {
		var tmp = typeof(route.meta.title) == 'function' ? route.meta.title(route) : '';
		document.title = tmp || route.meta.title || 'Music library';
	});
}

router.afterEach((to, from) => { updateTemporaryTitle(to) });
updateTemporaryTitle(router.currentRoute);