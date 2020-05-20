function emit_download(url) {
	let aTag = document.createElement('a');
	aTag.download = '';
	aTag.href = url;
	aTag.click()
}

const ap = new APlayer({
	container: document.getElementById('aplayer'),
	fixed: true,
	preload: 'auto',
	volume: 0.7,
	mutex: true,
	listFolded: true,
	listMaxHeight: 90,
	audio: []
});

function setPlayList(tracks, cur_play = 0) {
	axios.get('/api/songs/' + tracks.map(track => track.id).join() + '/play').then(response => {
		var files = response.data.data.files, covers = response.data.data.covers, al = [];
		try { ap.list.clear(); } catch(e) {}
		for (var i = 0; i < tracks.length; i++) {
			al.push({
				name: tracks[i].title,
				artist: tracks[i].artist,
				url: files[i],
				cover: covers[i]
			})
		}
		ap.list.add(al);
		ap.list.switch(cur_play);
		ap.play();
	})
}

const opts = { dark: false };
Vue.use(Vuetify);
Vue.use(VueViewer.default);

const Index = { template: '<div>test index</div>' }

Vue.component('text-edit', {
	template: `
	<span style="width:100%">
		<v-text-field v-model="text" v-if="editing" @blur="stop_edit" @input="debouncedPush()"></v-text-field>
		<span v-else> {{ text }} <v-btn text icon small><v-icon @click="start_edit">mdi-pencil</v-icon></v-btn></span>
	</span>
	`,
	props: ['text', 'pushurl', 'pushkey'],
	data: function() {
		return {
			editing: false
		}
	},
	created: function() {
		this.debouncedPush = _.debounce(() => { this.push() }, 300)
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
		<v-card-title><text-edit :text="scan.packname" :pushurl="'/api/scan/' + scan.id + '/update_name'" pushkey="name"></text-edit></v-card-title>
		<v-card-text>
			<div v-viewer="{url: 'data-src'}" class="images">
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
	</div>
	`,
	props: ['scan']
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

Vue.component('add-playlist', {
	template: `
	<div data-app>
		<v-dialog v-model="show" max-width="500" max-height="600">
			<v-card style="min-height:600px">
				<v-card-title>Choose target playlist</v-card-title>
				<v-card-text>
					<v-text-field v-model="search" label="Search for playlists" @input="debouncedSearch()"></v-text-field>
					<v-simple-table>
						<thead>
							<tr>
								<th class="text-left">Title</th>
								<th class="text-left">Count</th>
							</tr>
						</thead>
						<tbody style="cursor:pointer">
							<tr v-for="(item, key) in playlists" :key="'playlist' + item.id" @click="addTo(item)">
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
	props: [],
	data: function() {
		return {
			show: false,
			search: '',
			playlists: [],
		}
	},
	created: function() {
		this.debouncedSearch = _.debounce(() => { this.doSearch() }, 300)
	},
	methods: {
		add: function(track) {
			this.show = true;
			this.cur_track = track;
			this.doSearch();
		},
		doSearch: function() {
			axios.get('/api/playlist/search', {params: {query: this.search}}).then(response => {
				this.playlists = response.data.data;
			})
		},
		addTo: function(playlist) {
			axios.post('/api/playlist/' + playlist.id + '/addtrack', {song_id: this.cur_track.id}).then(response => {
				this.show = false
			})
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
					Artist: {{ artist }} <br>
					Release date: {{ release_date || 'Unknown' }} <br>
					Format: {{ format + ', ' + quality + ' (' + quality_details + ')'}} <br>
					Source: {{ source && file_source ? source + ', ' + file_source : source || file_source || 'Unknown' }} <br>
					Trusted: {{ trusted ? 'yes' : 'no' }} <br>
					Comments: {{ comments }} <br>
					<v-btn text small @click="edit()">Edit</v-btn>
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
			<v-tab> Scans </v-tab>
			<v-tab> Logs </v-tab>
			<v-tab> Other files </v-tab>
			<v-tab> Add files </v-tab>
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
				<v-card-title>Add scans</v-card-title>
				<file-upload label="File" :upload_handler="upload('scan')"></file-upload>
				<v-card-title>Add logs</v-card-title>
				<file-upload label="File" :upload_handler="upload('log')"></file-upload>
				<v-card-title>Add other files</v-card-title>
				<file-upload label="File" :upload_handler="upload('other')"></file-upload>
			</v-tab-item>
		</v-tabs>
		<add-playlist ref="add_playlist"></add-playlist>
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
			scans: []
		}
	},
	computed: {
		cover_default: function() {
			return this.cover_files.length ? this.cover_files[0] : 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY/j//z8DAAj8Av6IXwbgAAAAAElFTkSuQmCC';
		}
	},
	watch: {
		id: function(new_id, old_id) {
			this.init()
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
			})
			axios.get('/api/album/' + this.id + '/scans').then(response => {
				this.scans = response.data.data;
			})
		},
		download_song: function(item) {
			axios.get('/api/song/' + item.id + '/link').then(response => {
				emit_download(response.data.data.file);
			})
		},
		edit: function() {
			this.$router.push({ name: 'album_edit', params: { id: this.id } });
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
	watch: {
		id: function(new_id, old_id) {
			this.init()
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

const Playlist = {
	template: `
	<div>
		<v-row>
			<v-card-title> {{ title }} &nbsp; <v-btn text icon small><v-icon @click="edit">mdi-pencil</v-icon></v-btn></v-card-title>
			<v-card-text> {{ description }} </v-card-text>
		</v-row>
		<v-simple-table>
			<thead>
				<tr>
					<th class="text-left">#</th>
					<th class="text-left" style="min-width:100px"></th>
					<th class="text-left">Title</th>
					<th class="text-left">Duration</th>
					<th class="text-left">Artist</th>
					<th class="text-left">Album</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(item, key) in tracks" :key="'track' + item.id">
					<td>{{ key + 1 }}</td>
					<td>
						<v-btn text icon small v-on:click="setPlayList(tracks, key)"><v-icon>mdi-play-circle</v-icon></v-btn>
						<v-btn text icon small v-on:click="download_song(item)"><v-icon>mdi-download</v-icon></v-btn>
					</td>
					<td>{{ item.title }}</td>
					<td>{{ item.duration }}</td>
					<td>{{ item.artist }}</td>
					<td><router-link :to="'/album/' + item.album_id">{{ item.album_title }}</a></td>
				</tr>
			</tbody>
		</v-simple-table>
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
			})
		},
		download_song: function(item) {
			axios.get('/api/song/' + item.id + '/link').then(response => {
				emit_download(response.data.data.file);
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
			})
		},
		download_song: function(item) {
			axios.get('/api/song/' + item.id + '/link').then(response => {
				emit_download(response.data.data.file);
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

const router = new VueRouter({
	routes: [
		{ path: '/', component: Index },
		{ path: '/album/:id', component: Album, name: 'album' },
		{ path: '/album/:id/edit', component: AlbumEdit, name: 'album_edit' },
		{ path: '/playlist/:id', component: Playlist, name: 'playlist' },
		{ path: '/playlist/:id/edit', component: PlaylistEdit, name: 'playlist_edit' },
	]
})

new Vue({
	router,
	el: '#app',
	vuetify: new Vuetify(opts)
})
